from mailjet_rest import Client
from .configs import (
    MAILJET_API_KEY,
    MAILJET_API_SECRET,
    FROM_EMAIL,
    FROM_NAME,
)


def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    text_body: str,
    html_body: str = None,
) -> bool:
    print("sending email...")
    mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_API_SECRET), version="v3.1")
    data = {
        "Messages": [
            {
                "From": {"Email": FROM_EMAIL, "Name": FROM_NAME},
                "To": [{"Email": to_email, "Name": to_name}],
                "Subject": subject,
                "TextPart": text_body,
                "HTMLPart": html_body if html_body is not None else text_body,
                "CustomID": "AppGettingStartedTest",
            }
        ]
    }
    result = mailjet.send.create(data=data)
    print(result.status_code)
    print(result.json())
    return result.status_code == 200
