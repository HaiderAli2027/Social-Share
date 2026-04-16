from os import link
from wsgiref import headers

from httpx import get
import requests
from django.contrib.auth import get_user_model

class UserNotConnectedLinkedin(Exception):
    pass

def get_linkedin_user_details(user):
    try:
        linkedin_social = user.socialaccount_set.get(provider='linkedin')
    except:
        raise UserNotConnectedLinkedin("User is not connected to LinkedIn")
    return linkedin_social

def get_share_header(linkedin_social):
    tokens = linkedin_social.socialtoken_set.all()
    if not tokens.exists():
        raise Exception("Linkedin Connection is invalid. Please try login again.")
    social_token = tokens.first()
    return {
         "Authorization": f"Bearer {social_token.token}",
        "X-Restli-Protocol-Version": "2.0.0"
    }

def post_to_linkedin(user, text:str):
    User = get_user_model()
    if not isinstance(user, User):
        raise Exception("Must be a User")
    
    linkedin_social = get_linkedin_user_details(user)
    linkedin_user_id = linkedin_social.uid
    if not linkedin_user_id:
        raise Exception("Invalid Linkedin User id")
    headers = get_share_header(linkedin_social)
    endpoint = "https://api.linkedin.com/v2/ugcPosts"
    payload = {
        "author": f"urn:li:person:{linkedin_user_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": f"{text}"
                },
                "shareMediaCategory": "NONE"
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        }
    }
    response = requests.post(endpoint, json=payload, headers=headers)
    try:
        response.raise_for_status()
    except:
        raise Exception("Invalid post, please try again later")
    return response
