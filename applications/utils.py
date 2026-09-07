import binascii
import os
from urllib.request import urlretrieve

import requests
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import get_connection, EmailMultiAlternatives
from django.template import loader
from rest_framework import exceptions

from . import models

# qlow jdan kgnb upqv

def get_email_connection(my_username="support@wowtamilnadu.com", my_password="qlow jdan kgnb upqv"):
    smtp_host = 'smtp.gmail.com'
    smtp_port = 587
    smtp_use_tls = True
    return get_connection(host=smtp_host, port=smtp_port, username=my_username, password=my_password, use_tls=smtp_use_tls)


def send_email(to_email, context, subject_template_name, plain_body_template_name=None, html_body_template_name=None,
               bcc_email=None, cc_email=None):
    assert plain_body_template_name or html_body_template_name
    subject = loader.render_to_string(subject_template_name, context)
    subject = ''.join(subject.splitlines())
    if plain_body_template_name:
        html_body = loader.render_to_string(plain_body_template_name, context)
    else:
        html_body = loader.render_to_string(html_body_template_name, context)

    connection = get_email_connection()
    from_email = "support@wowtamilnadu.com"

    if not isinstance(to_email, list):
        to_email = [to_email]

    if not isinstance(bcc_email, list):
        bcc_email = [bcc_email] if bcc_email else []
    if not isinstance(cc_email, list):
        cc_email = [cc_email] if cc_email else []
    payload = {
        "subject": subject,
        "html_body": html_body,
        "from_email": from_email,
        "to_email": to_email,
        "cc": cc_email,
        "bcc": bcc_email,
    }

    try:
        # Change this to your actual API endpoint
        api_url = "https://crm.billiontags.com/api/"

        response = requests.post(api_url, json=payload, timeout=10)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("success"):
            print(f"✅ Email sent successfully to {to_email}")
        else:
            print(f"❌ Email API failed: {response_data}")
    except Exception as e:
        print(f"⚠️ Error calling email API: {e}")


def encode_uid(pk):
    try:
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        return urlsafe_base64_encode(force_bytes(pk)).decode()
    except ImportError:
        from django.utils.http import int_to_base36
        return int_to_base36(pk)


def decode_uid(pk):
    try:
        from django.utils.http import urlsafe_base64_decode
        from django.utils.encoding import force_text
        return force_text(urlsafe_base64_decode(pk))
    except ImportError:
        from django.utils.http import base36_to_int
        return base36_to_int(pk)


def get_or_create_token(user, client):
    token, created = models.Token.objects.get_or_create(client=client, user=user,
                                                        defaults={'user': user, 'client': client,
                                                                  'key': binascii.hexlify(os.urandom(20)).decode()})
    return token


class SendEmailViewMixin(object):
    token_generator = None
    subject_template_name = None
    plain_body_template_name = None
    html_body_template_name = None

    def __init__(self):
        self.request = None

    def send_email(self, to_email, context):
        send_email(to_email, context, **self.get_send_email_extras())

    def get_send_email_kwargs(self, user):
        return {
            'to_email': user.email,
            'context': self.get_email_context(user),
        }

    def get_send_email_extras(self):
        return {
            'subject_template_name': self.get_subject_template_name(),
            'plain_body_template_name': self.get_plain_body_template_name(),
            'html_body_template_name': self.get_html_body_template_name(),
        }

    def get_subject_template_name(self):
        return self.subject_template_name

    def get_plain_body_template_name(self):
        return self.plain_body_template_name

    def get_html_body_template_name(self):
        return self.html_body_template_name

    def get_email_context(self, user):
        token = self.token_generator.make_token(user)
        uid = encode_uid(user.pk)
        domain = settings.USER.get('DOMAIN') or get_current_site(self.request).domain
        site_name = settings.USER.get('SITE_NAME') or get_current_site(self.request).name
        return {
            'user': user,
            'domain': domain,
            'site_name': site_name,
            'uid': uid,
            'token': token,
            'protocol': 'https' if self.request.is_secure() else 'http',
        }


class ActionViewMixin(object):

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            return self.action(serializer)
        else:
            raise exceptions.ValidationError(serializer.errors)

    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            return self.action(serializer)
        else:
            raise exceptions.ValidationError(serializer.errors)


def get_download_image(local_path, image_url):
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    urlretrieve(image_url, local_path)
    return True
