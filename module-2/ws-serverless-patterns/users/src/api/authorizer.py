# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import os
import re
import json
import time
import urllib.request
from jose import jwk, jwt
from jose.utils import base64url_decode

# *** Section 1 : base setup and token validation helper function
is_cold_start = True
keys = {}
user_pool_id = os.getenv('USER_POOL_ID', None)
app_client_id = os.getenv('APPLICATION_CLIENT_ID', None)
admin_group_name = os.getenv('ADMIN_GROUP_NAME', None)

def validate_token(token, region):
    global keys, is_cold_start, user_pool_id, app_client_id
    if is_cold_start:
        # KEYS_URL -- REPLACE WHEN CHANGING IDENTITY PROVIDER!!
        keys_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
        with urllib.request.urlopen(keys_url) as f:
            response = f.read()
        keys = json.loads(response.decode('utf-8'))['keys']
        is_cold_start = False

    # get the kid from the headers prior to verification
    headers = jwt.get_unverified_headers(token)
    kid = headers['kid']
    # search for the kid in the downloaded public keys
    key_index = -1
    for i in range(len(keys)):
        if kid == keys[i]['kid']:
            key_index = i
            break
    if key_index == -1:
        print('Public key not found in jwks.json')
        return False
    # construct the public key
    public_key = jwk.construct(keys[key_index])
    # get the last two sections of the token,
    # message and signature (encoded in base64)
    message, encoded_signature = str(token).rsplit('.', 1)
    # decode the signature
    decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
    # verify the signature
    if not public_key.verify(message.encode("utf8"), decoded_signature):
        print('Signature verification failed')
        return False
    print('Signature successfully verified')
    # since verification succeeded, you can now safely use the unverified claims
    claims = jwt.get_unverified_claims(token)

    # Additionally you can verify the token expiration
    if time.time() > claims['exp']:
        print('Token is expired')
        return False
    # and the Audience  (use claims['client_id'] if verifying an access token)
    if claims['aud'] != app_client_id:
        print('Token was not issued for this audience')
        return False
    decoded_jwt = jwt.decode(token, key=keys[key_index], audience=app_client_id)
    return decoded_jwt

def lambda_handler(event, context):
    global admin_group_name
    tmp = event['methodArn'].split(':')
    api_gateway_arn_tmp = tmp[5].split('/')
    region = tmp[3]
    aws_account_id = tmp[4]
    # validate the incoming token
    validated_decoded_token = validate_token(event['authorizationToken'], region)
    if not validated_decoded_token:
        raise Exception('Unauthorized')
    principal_id = validated_decoded_token['sub']
    # initialize the policy
    policy = AuthPolicy(principal_id, aws_account_id)
    policy.restApiId = api_gateway_arn_tmp[0]
    policy.region = region
    policy.stage = api_gateway_arn_tmp[1]

    # *** Section 2 : authorization rules
    # Allow all public resources/methods explicitly

    # Add user specific resources/methods
    policy.allow_method(HttpVerb.GET, f"/users/{principal_id}")
    policy.allow_method(HttpVerb.PUT, f"/users/{principal_id}")
    policy.allow_method(HttpVerb.DELETE, f"/users/{principal_id}")
    policy.allow_method(HttpVerb.GET, f"/users/{principal_id}/*")
    policy.allow_method(HttpVerb.PUT, f"/users/{principal_id}/*")
    policy.allow_method(HttpVerb.DELETE, f"/users/{principal_id}/*")

    # Look for admin group in Cognito groups
    # Assumption: admin group always has higher precedence
    if 'cognito:groups' in validated_decoded_token and validated_decoded_token['cognito:groups'][0] == admin_group_name:
        # add administrative privileges
        policy.allow_method(HttpVerb.GET, "users")
        policy.allow_method(HttpVerb.GET, "users/*")
        policy.allow_method(HttpVerb.DELETE, "users")
        policy.allow_method(HttpVerb.DELETE, "users/*")
        policy.allow_method(HttpVerb.POST, "users")
        policy.allow_method(HttpVerb.PUT, "users/*")

    # Finally, build the policy
    auth_response = policy.build()
    return auth_response

# *** Section 3 : authorization policy helper classes
class HttpVerb:
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    HEAD = "HEAD"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    ALL = "*"

class AuthPolicy(object):
    awsAccountId = ""
    """The AWS account id the policy will be generated for. This is used to create the method ARNs."""
    principalId = ""
    """The principal used for the policy, this should be a unique identifier for the end user."""
    version = "2012-10-17"
    """The policy version used for the evaluation. This should always be '2012-10-17'"""
    pathRegex = "^[/.a-zA-Z0-9-\*]+$"
    """The regular expression used to validate resource paths for the policy"""

    allowMethods = []
    denyMethods = []

    restApiId = "<<restApiId>>"
    region = "<<region>>"
    stage = "<<stage>>"

    def __init__(self, principal, aws_account_id):
        self.awsAccountId = aws_account_id
        self.principalId = principal
        self.allowMethods = []
        self.denyMethods = []

    def _add_method(self, effect, verb, resource, conditions):
        if verb != "*" and not hasattr(HttpVerb, verb):
            raise NameError("Invalid HTTP verb " + verb + ". Allowed verbs in HttpVerb class")
        resource_pattern = re.compile(self.pathRegex)
        if not resource_pattern.match(resource):
            raise NameError("Invalid resource path: " + resource + ". Path should match " + self.pathRegex)

        if resource[:1] == "/":
            resource = resource[1:]

        resource_arn = ("arn:aws:execute-api:" +
                        self.region + ":" +
                        self.awsAccountId + ":" +
                        self.restApiId + "/" +
                        self.stage + "/" +
                        verb + "/" +
                        resource)

        if effect.lower() == "allow":
            self.allowMethods.append({
                'resourceArn': resource_arn,
                'conditions': conditions
            })
        elif effect.lower() == "deny":
            self.denyMethods.append({
                'resourceArn': resource_arn,
                'conditions': conditions
            })

    def _get_empty_statement(self, effect):
        statement = {
            'Action': 'execute-api:Invoke',
            'Effect': effect[:1].upper() + effect[1:].lower(),
            'Resource': []
        }
        return statement

    def _get_statement_for_effect(self, effect, methods):
        statements = []
        if len(methods) > 0:
            statement = self._get_empty_statement(effect)
            for curMethod in methods:
                if curMethod['conditions'] is None or len(curMethod['conditions']) == 0:
                    statement['Resource'].append(curMethod['resourceArn'])
                else:
                    conditional_statement = self._get_empty_statement(effect)
                    conditional_statement['Resource'].append(curMethod['resourceArn'])
                    conditional_statement['Condition'] = curMethod['conditions']
                    statements.append(conditional_statement)
            statements.append(statement)
        return statements

    def allow_all_methods(self):
        self._add_method("Allow", HttpVerb.ALL, "*", [])

    def deny_all_methods(self):
        self._add_method("Deny", HttpVerb.ALL, "*", [])

    def allow_method(self, verb, resource):
        self._add_method("Allow", verb, resource, [])

    def deny_method(self, verb, resource):
        self._add_method("Deny", verb, resource, [])

    def allow_method_with_conditions(self, verb, resource, conditions):
        self._add_method("Allow", verb, resource, conditions)

    def deny_method_with_conditions(self, verb, resource, conditions):
        self._add_method("Deny", verb, resource, conditions)

    def build(self):
        if ((self.allowMethods is None or len(self.allowMethods) == 0) and
                (self.denyMethods is None or len(self.denyMethods) == 0)):
            raise NameError("No statements defined for the policy")

        policy = {
            'principalId': self.principalId,
            'policyDocument': {
                'Version': self.version,
                'Statement': []
            }
        }

        policy['policyDocument']['Statement'].extend(self._get_statement_for_effect("Allow", self.allowMethods))
        policy['policyDocument']['Statement'].extend(self._get_statement_for_effect("Deny", self.denyMethods))

        return policy
