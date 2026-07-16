from __future__ import annotations
import os
import mimetypes
import traceback
import httpx
from core.logger import app_logs
from requests_toolbelt.multipart.encoder import MultipartEncoder
from typing import Dict, Any, List, Union
import re


class WhatsApp(object):
    """ "
    WhatsApp Object
    """

    def __init__(self, token:str=None, phone_number_id:int=None, wb_account_id:int=None, template_access_token:str=None)->None:
        """
        Initialize the WhatsApp Object

        Args:
            token[str]: Token for the WhatsApp cloud API obtained from the developer portal
            phone_number_id[str]: Phone number id for the WhatsApp cloud API obtained from the developer portal
        """

        self.token = token
        self.phone_number_id = phone_number_id
        self.wb_account_id = wb_account_id
        self.base_version = "v17.0"
        self.templates_base_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.base_version}"
        self.url = f"{self.base_url}/{phone_number_id}/messages"
        self.media_url = f"{self.base_url}/{phone_number_id}/media"
        self.temp_message = 'message_templates'
        self.message_template_url = f"https://graph.facebook.com/{self.templates_base_version}/{self.wb_account_id}/{self.temp_message}"
        self.template_access_token = template_access_token 

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(self.token),
        }

        self.media_headers =  {
            "Authorization": "Bearer {}".format(self.token),
        }

        self.template_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(self.template_access_token),
        }

        self.timeout_settings = httpx.Timeout(30.0, connect=10.0)
        

    async def send_message(
            self, message, recipient_id, recipient_type="individual", preview_url=True, reply_to=""
    ):
        try:
            """
            Sends a text message to a WhatsApp user

            Args:
                    message[str]: Message to be sent to the user
                    recipient_id[str]: Phone number of the user with country code wihout +
                    recipient_type[str]: Type of the recipient, either individual or group
                    preview_url[bool]: Whether to send a preview url or not

            Example:
                ```python
                >>> from whatsapp import WhatsApp
                >>> whatsapp = WhatsApp(token, phone_number_id)
                >>> await whatsapp.send_message("Hello World", "5511999999999")
                >>> await whatsapp.send_message("Hello World", "5511999999999", preview_url=False)

            """
            data = {
                "messaging_product": "whatsapp",
                "recipient_type": recipient_type,
                "to": recipient_id,
                "type": "text",
                "text": {"preview_url": preview_url, "body": message},
            }

            if reply_to:
                data["context"] = {
                    "message_id": reply_to
                }
            app_logs("INFO", f"Sending message to {recipient_id} {reply_to}")
            async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
                response = await client.post(self.url, headers=self.headers, json=data)

            if response.status_code == 200:
                app_logs("INFO",f"Message sent to {recipient_id}")
                return response.json()
            else:
                app_logs("INFO", f"Message not sent to {recipient_id}: {response.status_code}")
                app_logs("ERROR",f"Response: {response.text}")

            return response.json()
        except Exception as e:
            app_logs("ERROR", "Failed to get item data ", {"error": str(traceback.format_exc()), "inputData": {"item_data"}})    

    async def send_reaction(self, emoji, message_id, recipient_id, recipient_type="individual"):
        """
        Sends a reaction message to a WhatsApp user's message asynchronously.

        Args:
            emoji (str): Emoji to become a reaction to a message. (😀)
            message_id (str): Message id for a reaction to be attached to
            recipient_id (str): Phone number of the user with country code without +
            recipient_type (str): Type of the recipient, either individual or group

        Example:
            ```python
            from whatsapp import WhatsApp
            whatsapp = WhatsApp(token, phone_number_id)
            await whatsapp.send_reaction("", "wamid.HBgLM...", "5511999999999")
            ```
        """
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": recipient_id,
            "type": "reaction",
            "reaction": {"message_id": message_id, "emoji": emoji},
        }
        app_logs("INFO", f"Sending reaction to number {recipient_id} message id {message_id}")
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("INFO", f"Reaction sent to number {recipient_id} message id {message_id}")
            return response.json()
        else:
            app_logs("INFO", f"Reaction not sent to number {recipient_id} message id {message_id}: {response.status_code}")
            app_logs("error", (f"Response: {response.text}"))

        return response.json()

    async def reply_to_message(self, message_id: str, recipient_id: str, message: str, preview_url: bool = True):
        """
        Asynchronously replies to a message on WhatsApp.

        Args:
            message_id (str): Message id of the message to be replied to.
            recipient_id (str): Phone number of the user with country code without '+'.
            message (str): Message to be sent to the user.
            preview_url (bool): Whether to send a preview url or not.
        """
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "text",
            "context": {"message_id": message_id},
            "text": {"preview_url": preview_url, "body": message},
        }

        app_logs("info", (f"Replying to {message_id} for {recipient_id}"))
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("info", (f"Message replied to {recipient_id}"))
            return response.json()
        else:
            app_logs("info", (f"Failed to reply to {recipient_id}: {response.status_code}"))
            app_logs("error", (f"Response: {response.text}"))
            return response.json()

    async def send_template(self, template, recipient_id, components, lang: str = "en_US"):
        """
        Asynchronously sends a template message to a WhatsApp user. Templates can be:
            1. Text template
            2. Media based template
            3. Interactive template
        You can customize the template message by passing a dictionary of components.
        Find available components in the documentation:
        https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates

        Args:
            template (str): Template name to be sent to the user.
            recipient_id (str): Phone number of the user with country code without +.
            components (list): List of components to be sent to the user.
            lang (str): Language of the template message, default is "en_US".

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.send_template("hello_world", "5511999999999", components=[{"type": "header", "parameters": [{"type": "text", "text": "Header Text"}]}], lang="en_US")
        """
        data = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "template",
            "template": {
                "name": template,
                "language": {"code": lang},
                "components": components,
            },
        }
        
        app_logs("info", (f"Sending template to {recipient_id}"))
        app_logs("info", (f"Sending template data {data}"))
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("info", (f"Template sent to {recipient_id}"))
            return response.json()
        else:
            app_logs("info", (f"Template not sent to {recipient_id}: {response.status_code}"))
            app_logs("error", (f"Response: {response.text}"))
            return response.json()

    async def send_location(self, lat, long, name, address, recipient_id, reply_to=""):
        """
        Asynchronously sends a location message to a WhatsApp user.

        Args:
            lat (str): Latitude of the location.
            long (str): Longitude of the location.
            name (str): Name of the location.
            address (str): Address of the location.
            recipient_id (str): Phone number of the user with country code without +.

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.send_location("-23.564", "-46.654", "My Location", "Rua dois, 123", "5511999999999")
        """
        data = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "location",
            "location": {
                "latitude": lat,
                "longitude": long,
                "name": name,
                "address": address,
            },
        }
        if reply_to:
            data["context"] = {
                "message_id": reply_to
            }

        app_logs("info", (f"Sending location to {recipient_id} : {reply_to}"))
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("info", (f"Location sent to {recipient_id}"))
            return response.json()
        else:
            app_logs("info", (f"Location not sent to {recipient_id}: {response.status_code}"))
            app_logs("error", (f"Response: {response.text}"))
            return response.json()

    async def send_image(
            self,
            image,
            recipient_id,
            recipient_type="individual",
            caption=None,
            link=True,
            reply_to=""
    ):
        """
        Asynchronously sends an image message to a WhatsApp user. The image can be sent by specifying either
        an image ID or a link to the image.

        Args:
            image (str): Image ID or link to the image.
            recipient_id (str): Phone number of the user with country code without +.
            recipient_type (str): Type of the recipient, either individual or group.
            caption (str, optional): Caption for the image.
            link (bool): True if sending by image ID, False if sending by image link.

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.send_image("https://i.imgur.com/Fh7XVYY.jpeg", "5511999999999")
        """
        if link:
            data = {
                "messaging_product": "whatsapp",
                "recipient_type": recipient_type,
                "to": recipient_id,
                "type": "image",
                "image": {"link": image, "caption": caption},
            }
        else:
            data = {
                "messaging_product": "whatsapp",
                "recipient_type": recipient_type,
                "to": recipient_id,
                "type": "image",
                "image": {"id": image, "caption": caption},
            }

        if reply_to:
            data["context"] = {
                "message_id": reply_to
            }

        app_logs("info", (f"Sending image to {recipient_id}:{reply_to}"))
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("info", (f"Image sent to {recipient_id}"))
            return response.json()
        else:
            app_logs("info", (f"Image not sent to {recipient_id}: {response.status_code}"))
            app_logs("error", (f"Response: {response.text}"))
            return response.json()

    async def send_sticker(self, sticker: str, recipient_id: str, recipient_type="individual", link=True):
        """
        Asynchronously sends a sticker message to a WhatsApp user.

        There are two ways to send a sticker message to a user, either by passing the sticker id or by passing the sticker link.
        Sticker id is the id of the sticker uploaded to the cloud API.

        Args:
            sticker (str): Sticker id or link of the sticker.
            recipient_id (str): Phone number of the user with country code without +.
            recipient_type (str): Type of the recipient, either individual or group.
            link (bool): Whether to send a sticker id or a sticker link, True means that the sticker is an id, False means the sticker is a link.

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.send_sticker("https://link_to_sticker_image.png", "5511999999999", link=True)
        """
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": recipient_type,
            "to": recipient_id,
            "type": "sticker",
            "sticker": {"link": sticker} if link else {"id": sticker},
        }

        app_logs("info",f"Sending sticker to {recipient_id}")
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("info",f"Sticker sent to {recipient_id}")
            return response.json()
        else:
            app_logs("info",f"Sticker not sent to {recipient_id}: {response.status_code}")
            app_logs("error",f"Response: {response.text}")
            return response.json()

    async def send_audio(self, audio, recipient_id, link=True, reply_to=""):
        """
        Asynchronously sends an audio message to a WhatsApp user. Audio messages can be sent by either passing the audio ID or by passing the audio link.

        Args:
            audio (str): Audio ID or link of the audio.
            recipient_id (str): Phone number of the user with country code without +.
            link (bool): Whether to send an audio ID or an audio link, True means that the audio is an ID, False means that the audio is a link.

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.send_audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", "5511999999999")
        """
        data = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "audio",
            "audio": {"link": audio} if link else {"id": audio},
        }
        if reply_to:
            data["context"] = {
                "message_id": reply_to
            }

        app_logs("info",f"Sending audio to {recipient_id} : {reply_to}")
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("info",f"Audio sent to {recipient_id}")
            return response.json()
        else:
            app_logs("info",f"Audio not sent to {recipient_id}: {response.status_code}")
            app_logs("error",f"Response: {response.text}")
            return response.json()

    async def send_video(self, video: str, recipient_id: str, caption: str = None, link: bool = True, reply_to: str = '') -> Dict[Any, Any]:
        """
        Asynchronously sends a video message to a WhatsApp user. Video messages can either be sent by passing the video ID or by passing the video link.

        Args:
            video (str): Video ID or link of the video.
            recipient_id (str): Phone number of the user with country code without +.
            caption (str, optional): Caption of the video.
            link (bool): Whether to send a video ID or a video link, True means that the video is an ID, False means that the video is a link.

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.send_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "5511999999999")
        """
        data = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "video",
            "video": {"link": video, "caption": caption} if link else {"id": video, "caption": caption},
        }

        if reply_to:
            data["context"] = {
                "message_id": reply_to
            }

        app_logs("info",f"Sending video to {recipient_id} : {reply_to}")
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("info",f"Video sent to {recipient_id}")
            return response.json()
        else:
            app_logs("info",f"Video not sent to {recipient_id}: {response.status_code}")
            app_logs("error",f"Response: {response.text}")
            return response.json()

    async def send_custom_json(self, data, recipient_id=None):
        """
        Asynchronously sends a custom JSON to a WhatsApp user. This can be used to send custom objects to the message endpoint.

        Args:
            data (dict): Dictionary that should be sent.
            recipient_id (str, optional): Phone number of the user with country code without +.

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.send_custom_json({
                    "messaging_product": "whatsapp",
                    "type": "audio",
                    "audio": {"id": "audio_id"}}, "5511999999999")
        """
        if recipient_id:
            if "to" not in data:
                data["to"] = recipient_id
                app_logs("info",f"Setting recipient_id to {recipient_id}")

        app_logs("info",f"Sending custom JSON to {recipient_id if recipient_id else 'unspecified recipient'}")
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("info",f"Custom JSON sent to {recipient_id if recipient_id else 'unspecified recipient'}")
            return response.json()
        else:
            app_logs("info",
                f"Custom JSON not sent to {recipient_id if recipient_id else 'unspecified recipient'}: {response.status_code}")
            app_logs("error",f"Response: {response.text}")
            return response.json()

    async def send_document(self, document: str, recipient_id: str, caption: str = None, link: bool = True,
                            filename: str = None, reply_to:str = None) -> Dict[Any, Any]:
        """
        Asynchronously sends a document message to a WhatsApp user. Documents can either be sent by passing the document ID or by passing the document link.

        Args:
            document (str): Document ID or link of the document.
            recipient_id (str): Phone number of the user with country code without +.
            caption (str, optional): Caption of the document.
            link (bool): Whether to send a document ID or a document link, True means the document is an ID, False means the document is a link.
            filename (str, optional): Name of the file if sending by link.

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.send_document("https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf", "5511999999999")
        """
        if link:
            data = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "document",
                "document": {"link": document, "caption": caption, "filename": filename},
            }
        else:
            data = {
                "messaging_product": "whatsapp",
                "to": recipient_id,
                "type": "document",
                "document": {"id": document, "caption": caption},
            }

        if reply_to:
            data["context"] = {
                "message_id": reply_to
            }

        app_logs("info",f"Sending document to {recipient_id} : {reply_to}")
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("info",f"Document sent to {recipient_id}")
            return response.json()
        else:
            app_logs("info",f"Document not sent to {recipient_id}: {response.status_code}")
            app_logs("error",f"Response: {response.text}")
            return response.json()

    async def send_contacts(
            self, contacts: List[Dict[Any, Any]], recipient_id: str, reply_to: str
    ) -> Dict[Any, Any]:
        """
        Asynchronously sends a list of contacts to a WhatsApp user.

        Args:
            contacts (List[Dict[Any, Any]]): List of contacts to send, structured according to the WhatsApp API requirements.
            recipient_id (str): Phone number of the user with country code without +.

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> contacts = [{
                "addresses": [{
                    "street": "STREET",
                    "city": "CITY",
                    "state": "STATE",
                    "zip": "ZIP",
                    "country": "COUNTRY",
                    "country_code": "COUNTRY_CODE",
                    "type": "HOME"
                    }],
                ...
                }]
            >>> await whatsapp.send_contacts(contacts, "5511999999999")

        REFERENCE:
        https://developers.facebook.com/docs/whatsapp/cloud-api/reference/messages#contacts-object
        """

        data = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "contacts",
            "contacts": [contacts],
        }
        if reply_to:
            data["context"] = {
                "message_id": reply_to
            }

        app_logs("info",f"Sending contacts to {recipient_id} : {reply_to}")
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("info",f"Contacts sent to {recipient_id}")
            return response.json()
        else:
            app_logs("info",f"Contacts not sent to {recipient_id}: {response.status_code}")
            app_logs("error",f"Response: {response.text}")
            return response.json()

    async def upload_media(self, media: str) -> Union[Dict[Any, Any], None]:
        """
        Asynchronously uploads a media file to the cloud API and returns the ID of the media.

        Args:
            media (str): Path of the media to be uploaded.

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.upload_media("/path/to/media")

        REFERENCE:
        https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media#
        """
        content_type, _ = mimetypes.guess_type(media)
        headers = self.headers.copy()
        app_logs("info",f"Uploading media {media}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout_settings) as client, open(os.path.realpath(media), 'rb') as file:
                files = {'file': (os.path.basename(media), file, content_type)}
                data = {
                    'messaging_product': 'whatsapp',
                    'type': content_type
                }
                response = await client.post(
                    f"{self.base_url}/{self.phone_number_id}/media",
                    headers=headers,
                    files=files,
                    data=data
                )

            if response.status_code == 200:
                app_logs("info",f"Media {media} uploaded")
                return response.json()
            else:
                app_logs("info",f"Error uploading media {media}")
                app_logs("info",f"Status code: {response.status_code}")
                app_logs("info",f"Response: {response.text}")
                return None
        except Exception as e:
            app_logs("error",f"Exception occurred while uploading media: {str(e)}")
            return None

    async def delete_media(self, media_id: str) -> Union[Dict[Any, Any], None]:
        """
        Asynchronously deletes a media from the cloud API.

        Args:
            media_id (str): ID of the media to be deleted.
        """
        app_logs("info",f"Deleting media {media_id}")
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.delete(f"{self.base_url}/{media_id}", headers=self.headers)

        if response.status_code == 200:
            app_logs("info",f"Media {media_id} deleted")
            return response.json()
        else:
            app_logs("info",f"Error deleting media {media_id}: {response.status_code}")
            app_logs("error",f"Response: {response.text}")
            return None

    async def mark_as_read(self, message_id: str) -> Dict[Any, Any]:
        """
        Asynchronously marks a message as read using the WhatsApp Cloud API.

        Args:
            message_id (str): ID of the message to be marked as read.

        Returns:
            Dict[Any, Any]: Response from the API.

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.mark_as_read("message_id")
        """
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        json_data = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        app_logs("info",f"Marking message {message_id} as read")
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(
                f"{self.v15_base_url}/{self.phone_number_id}/messages",
                headers=headers,
                json=json_data,
            )

        if response.status_code == 200:
            app_logs("info",f"Message {message_id} marked as read")
            return response.json()
        else:
            app_logs("info",f"Error marking message {message_id} as read: {response.status_code}")
            app_logs("error",f"Response: {response.text}")
            return response.json()

    def create_button(self, button: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        Method to create a button object to be used in the send_message method.

        This is method is designed to only be used internally by the send_button method.

        Args:
               button[dict]: A dictionary containing the button data
        """
        data = {"type": "list", "action": button.get("action")}
        if button.get("header"):
            data["header"] = {"type": "text", "text": button.get("header")}
        if button.get("body"):
            data["body"] = {"text": button.get("body")}
        if button.get("footer"):
            data["footer"] = {"text": button.get("footer")}
        return data

    async def send_button(self, button: Dict[Any, Any], recipient_id: str) -> Dict[Any, Any]:
        """
        Asynchronously sends an interactive buttons message to a WhatsApp user.

        Args:
            button (dict): A dictionary containing the button data (rows-title may not exceed 20 characters).
            recipient_id (str): Phone number of the user with country code without +.

        Check https://github.com/Neurotech-HQ/heyoo#sending-interactive-reply-buttons for an example.
        """
        data = {
            "messaging_product": "whatsapp",
            "to": recipient_id,
            "type": "interactive",
            "interactive": self.create_button(button),
        }

        app_logs("info",f"Sending buttons to {recipient_id}")
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("info",f"Buttons sent to {recipient_id}")
            return response.json()
        else:
            app_logs("info",f"Buttons not sent to {recipient_id}: {response.status_code}")
            app_logs("error",f"Response: {response.text}")
            return response.json()

    async def send_reply_button(self, button: Dict[Any, Any], recipient_id: str) -> Dict[Any, Any]:
        """
        Asynchronously sends an interactive reply buttons [menu] message to a WhatsApp user.

        Args:
            button (dict): A dictionary containing the button data.
            recipient_id (str): Phone number of the user with country code without +.

        Note:
            The maximum number of buttons is 3; more than 3 buttons will raise an error.
        """
        data = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_id,
            "type": "interactive",
            "interactive": button,
        }

        app_logs("info",f"Sending reply buttons to {recipient_id}")
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(self.url, headers=self.headers, json=data)

        if response.status_code == 200:
            app_logs("info",f"Reply buttons sent to {recipient_id}")
            return response.json()
        else:
            app_logs("info",f"Reply buttons not sent to {recipient_id}: {response.status_code}")
            app_logs("error",f"Response: {response.text}")
            return response.json()

    async def query_media_url(self, media_id: str) -> Union[str, None]:
        """
        Asynchronously query media URL from a media ID obtained either by manually uploading media or received media.

        Args:
            media_id (str): Media ID of the media.

        Returns:
            str: Media URL, or None if not found or an error occurred.

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.query_media_url("media_id")
        """
        app_logs("info",f"DEBUG headers {self.headers}")
        app_logs("info",f"Querying media URL for {media_id}")
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.get(f"{self.base_url}/{media_id}", headers=self.headers)

        if response.status_code == 200:
            app_logs("info",f"Media URL queried for {media_id}")
            return response.json().get("url")
        else:
            app_logs("info",f"Media URL not queried for {media_id}: {response.status_code}")
            app_logs("info",f"Response: {response.text}")
            return None

    async def download_media(self, media_url: str, mime_type: str, file_path: str = "temp") -> Union[str, None]:
        """
        Asynchronously download media from a media URL obtained either by manually uploading media or received media.
        """
        extension = mime_type.split("/")[1].split(";")[0].strip()
        save_file_here = f"{file_path}.{extension}" if file_path else f"temp.{extension}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
                # FIX: Added headers=self.headers to authenticate the download request
                response = await client.get(media_url, headers=self.headers)

            if response.status_code == 200:
                # Ensure the directory exists
                os.makedirs(os.path.dirname(save_file_here), exist_ok=True)
                with open(save_file_here, "wb") as f:
                    f.write(response.content)
                app_logs("info", f"Media downloaded to {save_file_here}")
                return save_file_here
            else:
                app_logs("error", f"Failed to download media. Status code: {response.status_code}")
                # Optional: log response.text here to see exactly what Meta is complaining about
                app_logs("error", f"Response: {response.text}")
                return None
                
        except Exception as e:
            app_logs("error", f"Error downloading media to {save_file_here}: {str(e)}")
            return None

    def preprocess(self, data: Dict[Any, Any]) -> Dict[Any, Any]:
        """
        Preprocesses the data received from the webhook.

        This method is designed to only be used internally.

        Args:
            data[dict]: The data received from the webhook
        """
        return data["entry"][0]["changes"][0]["value"]

    def is_message(self, data: Dict[Any, Any]) -> bool:
        """is_message checks if the data received from the webhook is a message.

        Args:
            data (Dict[Any, Any]): The data received from the webhook

        Returns:
            bool: True if the data is a message, False otherwise
        """
        data = self.preprocess(data)
        if "messages" in data:
            return True
        else:
            return False
        
    def get_waba_id(self, data: Dict[Any, Any]) -> Union[str, None]:
        """
        Extracts the WhatsApp Business Account (WABA) ID from the webhook data.

        Args:
            data[dict]: The raw data received from the webhook
        Returns:
            str: The WABA ID, or None if not found
            
        Example:
            >>> waba_id = whatsapp.get_waba_id(data)
        """
        try:
            return data["entry"][0]["id"]
        except (KeyError, IndexError):
            return None

    def get_mobile(self, data: Dict[Any, Any]) -> Union[str, None]:
        """
        Extracts the mobile number of the sender from the data received from the webhook.

        Args:
            data[dict]: The data received from the webhook
        Returns:
            str: The mobile number of the sender

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> mobile = whatsapp.get_mobile(data)
        """
        data = self.preprocess(data)
        if "contacts" in data:
            return data["contacts"][0]["wa_id"]

    def get_name(self, data: Dict[Any, Any]) -> Union[str, None]:
        """
        Extracts the name of the sender from the data received from the webhook.

        Args:
            data[dict]: The data received from the webhook
        Returns:
            str: The name of the sender
        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> mobile = whatsapp.get_name(data)
        """
        contact = self.preprocess(data)
        if contact:
            return contact["contacts"][0]["profile"]["name"]

    def get_message(self, data: Dict[Any, Any]) -> Union[str, None]:
        """
        Extracts the text message of the sender from the data received from the webhook.

        Args:
            data[dict]: The data received from the webhook
        Returns:
            str: The text message received from the sender
        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> message = message.get_message(data)
        """
        data = self.preprocess(data)
        if "messages" in data:
            return data["messages"][0]["text"]["body"]

    def get_message_id(self, data: Dict[Any, Any]) -> Union[str, None]:
        """
        Extracts the message id of the sender from the data received from the webhook.

        Args:
            data[dict]: The data received from the webhook
        Returns:
            str: The message id of the sender
        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> message_id = whatsapp.get_message_id(data)
        """
        data = self.preprocess(data)
        if "messages" in data:
            return data["messages"][0]["id"]
        
    def get_message_reply_id(self, data: Dict[Any, Any]) -> Union[str, None]:
        """
        Extracts the message ID (wamid) of the incoming message from the webhook data.

        Args:
            data[dict]: The data received from the webhook
        Returns:
            str: The message ID (wamid) received from the sender, or None if missing
        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> message_id = whatsapp.get_message_id(data)
        """
        data = self.preprocess(data)
        if "messages" in data and len(data["messages"]) > 0:
            return data["messages"][0].get("id")
        return None

    def get_message_timestamp(self, data: Dict[Any, Any]) -> Union[str, None]:
        """ "
        Extracts the timestamp of the message from the data received from the webhook.

        Args:
            data[dict]: The data received from the webhook
        Returns:
            str: The timestamp of the message
        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> whatsapp.get_message_timestamp(data)
        """
        data = self.preprocess(data)
        if "messages" in data:
            return data["messages"][0]["timestamp"]

    def get_interactive_response(self, data: Dict[Any, Any]) -> Union[Dict, None]:
        """
         Extracts the response of the interactive message from the data received from the webhook.

         Args:
            data[dict]: The data received from the webhook
        Returns:
            dict: The response of the interactive message

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> response = whatsapp.get_interactive_response(data)
            >>> interactive_type = response.get("type")
            >>> message_id = response[interactive_type]["id"]
            >>> message_text = response[interactive_type]["title"]
        """
        data = self.preprocess(data)
        if "messages" in data:
            if "interactive" in data["messages"][0]:
                return data["messages"][0]["interactive"]

    def get_location(self, data: Dict[Any, Any]) -> Union[Dict, None]:
        """
        Extracts the location of the sender from the data received from the webhook.

        Args:
            data[dict]: The data received from the webhook

        Returns:
            dict: The location of the sender

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> whatsapp.get_location(data)
        """
        data = self.preprocess(data)
        if "messages" in data:
            if "location" in data["messages"][0]:
                return data["messages"][0]["location"]

    def get_image(self, data: Dict[Any, Any]) -> Union[Dict, None]:
        """ "
        Extracts the image of the sender from the data received from the webhook.

        Args:
            data[dict]: The data received from the webhook
        Returns:
            dict: The image_id of an image sent by the sender

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> image_id = whatsapp.get_image(data)
        """
        data = self.preprocess(data)
        if "messages" in data:
            if "image" in data["messages"][0]:
                return data["messages"][0]["image"]

    def get_document(self, data: Dict[Any, Any]) -> Union[Dict, None]:
        """ "
        Extracts the document of the sender from the data received from the webhook.

        Args:
            data[dict]: The data received from the webhook
        Returns:
            dict: The document_id of an image sent by the sender

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> document_id = whatsapp.get_document(data)
        """
        data = self.preprocess(data)
        if "messages" in data:
            if "document" in data["messages"][0]:
                return data["messages"][0]["document"]

    def get_audio(self, data: Dict[Any, Any]) -> Union[Dict, None]:
        """
        Extracts the audio of the sender from the data received from the webhook.

        Args:
            data[dict]: The data received from the webhook

        Returns:
            dict: The audio of the sender

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> whatsapp.get_audio(data)
        """
        data = self.preprocess(data)
        if "messages" in data:
            if "audio" in data["messages"][0]:
                return data["messages"][0]["audio"]

    def get_video(self, data: Dict[Any, Any]) -> Union[Dict, None]:
        """
        Extracts the video of the sender from the data received from the webhook.

        Args:
            data[dict]: The data received from the webhook

        Returns:
            dict: Dictionary containing the video details sent by the sender

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> whatsapp.get_video(data)
        """
        data = self.preprocess(data)
        if "messages" in data:
            if "video" in data["messages"][0]:
                return data["messages"][0]["video"]

    def get_message_type(self, data: Dict[Any, Any]) -> Union[str, None]:
        """
        Gets the type of the message sent by the sender from the data received from the webhook.


        Args:
            data [dict]: The data received from the webhook

        Returns:
            str: The type of the message sent by the sender

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> whatsapp.get_message_type(data)
        """
        data = self.preprocess(data)
        if "messages" in data:
            return data["messages"][0]["type"]

    def get_delivery(self, data: Dict[Any, Any]) -> Union[Dict, None]:
        """
        Extracts the delivery status of the message from the data received from the webhook.
        Args:
            data [dict]: The data received from the webhook

        Returns:
            dict: The delivery status of the message and message id of the message
        """
        data = self.preprocess(data)
        if "statuses" in data:
            return data["statuses"][0]["status"]

    def changed_field(self, data: Dict[Any, Any]) -> str:
        """
        Helper function to check if the field changed in the data received from the webhook.

        Args:
            data [dict]: The data received from the webhook

        Returns:
            str: The field changed in the data received from the webhook

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> whatsapp.changed_field(data)
        """
        return data["entry"][0]["changes"][0]["field"]


    def extract_body_parameters(self, original_template_body: str, filled_body: str) -> list:
        """
        Extract variable values by matching filled body against template with {{N}} placeholders.
        """
        escaped = re.escape(original_template_body)
        pattern = re.sub(r'\\\{\\\{(\d+)\\\}\\\}', '(.*?)', escaped)
        pattern = f"^{pattern}$"
        
        match = re.match(pattern, filled_body.strip(), re.DOTALL)
        if match:
            return list(match.groups())
        
        return []


    def build_whatsapp_components(self, raw_components, original_template_body: str = None) -> list:
        components = []

        if "header" in raw_components:
            header = raw_components["header"]
            header_type = header.get("type", "").upper()

            if header_type == "IMAGE":
                media_url = header.get("mediaUrl") or header.get("media")
                if media_url:
                    components.append({
                        "type": "header",
                        "parameters": [{"type": "image", "image": {"link": media_url}}]
                    })

            elif header_type == "VIDEO":
                media_url = header.get("mediaUrl") or header.get("media")
                if media_url:
                    components.append({
                        "type": "header",
                        "parameters": [{"type": "video", "video": {"link": media_url}}]
                    })

            elif header_type == "TEXT":
                params = header.get("parameters", [])
                if params:
                    components.append({"type": "header", "parameters": params})

        body_params = raw_components.get("bodyParameters", [])
        
        if not body_params and original_template_body and "body" in raw_components:
            filled_body = raw_components["body"]
            # print(f"[DEBUG] original_template_body: {repr(original_template_body)}")
            # print(f"[DEBUG] filled_body:             {repr(filled_body)}")
            body_params = self.extract_body_parameters(original_template_body, filled_body)
            # print(f"[DEBUG] extracted body_params:   {body_params}")
            
        if body_params:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": str(p)} for p in body_params]
            })

        if "buttons" in raw_components:
            buttons_data = raw_components["buttons"]
            if isinstance(buttons_data, dict):
                all_buttons = []
                for sub_type_key, btn_list in buttons_data.items():
                    if isinstance(btn_list, list):
                        for btn in btn_list:
                            if isinstance(btn, dict):
                                btn["_sub_type"] = "quick_reply" if sub_type_key == "quickReplies" else "url"
                                all_buttons.append(btn)
                buttons_data = all_buttons

            for idx, button in enumerate(buttons_data):
                if not isinstance(button, dict):
                    continue
                if button.get("parameters"):
                    components.append({
                        "type": "button",
                        "sub_type": button.get("_sub_type") or button.get("sub_type", "quick_reply"),
                        "index": str(idx),
                        "parameters": button["parameters"]
                    })

        return components
    
    async def list_template(self):
        """
        Asynchronously sends a template message to a WhatsApp user. Templates can be:
            1. Text template
            2. Media based template
            3. Interactive template
        You can customize the template message by passing a dictionary of components.
        Find available components in the documentation:
        https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates

        Args:
            template (str): Template name to be sent to the user.
            recipient_id (str): Phone number of the user with country code without +.
            components (list): List of components to be sent to the user.
            lang (str): Language of the template message, default is "en_US".

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.send_template("hello_world", "5511999999999", components=[{"type": "header", "parameters": [{"type": "text", "text": "Header Text"}]}], lang="en_US")
        """

        resp = {'error' : False, 'data' : None}
        app_logs("info", (f"Listing template {self.message_template_url}"))
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.get(self.message_template_url, headers=self.template_headers)

        if response.status_code == 200:
            resp = {'error' : False, 'data' : response.json()}
            return resp
        else:
            app_logs("info", (f"Template list {self.wb_account_id}: {response.status_code}"))
            app_logs("error", (f"Response: {response.text}"))
            resp = {'error' : True, 'data' : response.json()}
            return resp
        
    async def submit_template(self, data:str):
        """
        Asynchronously sends a template message to a WhatsApp user. Templates can be:
            1. Text template
            2. Media based template
            3. Interactive template
        You can customize the template message by passing a dictionary of components.
        Find available components in the documentation:
        https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates

        Args:
            template (str): Template name to be sent to the user.
            recipient_id (str): Phone number of the user with country code without +.
            components (list): List of components to be sent to the user.
            lang (str): Language of the template message, default is "en_US".

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.send_template("hello_world", "5511999999999", components=[{"type": "header", "parameters": [{"type": "text", "text": "Header Text"}]}], lang="en_US")
        """
        
        resp = {'error' : False, 'data' : None}
        app_logs("info", (f"submitting template {self.message_template_url}"))
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(self.message_template_url, headers=self.template_headers, json=data)
        
        if response.status_code == 200:
            resp = {'error' : False, 'data' : response.json()}
            return resp
        else:
            app_logs("info", (f"submitting Template {self.wb_account_id}: {response.status_code}"))
            app_logs("error", (f"Response: {response.text}"))
            resp = {'error' : True, 'data' : response.json()}
            return resp
        
    async def delete_template(self, template_name:str):
        """
        Asynchronously sends a template message to a WhatsApp user. Templates can be:
            1. Text template
            2. Media based template
            3. Interactive template
        You can customize the template message by passing a dictionary of components.
        Find available components in the documentation:
        https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates

        Args:
            template (str): Template name to be sent to the user.
            recipient_id (str): Phone number of the user with country code without +.
            components (list): List of components to be sent to the user.
            lang (str): Language of the template message, default is "en_US".

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.send_template("hello_world", "5511999999999", components=[{"type": "header", "parameters": [{"type": "text", "text": "Header Text"}]}], lang="en_US")
        """
        
        resp = {'error' : False, 'data' : None}
        
        async with httpx.AsyncClient(timeout=60) as client:
            url = f"{self.message_template_url}?name={template_name}"
            app_logs("info", (f"delete template {url} {template_name}"))
            response = await client.delete(url, headers=self.template_headers)
        
        if response.status_code == 200:
            resp = {'error' : False, 'data' : response.json()}
            return resp
        else:
            app_logs("info", (f"delete Template {self.wb_account_id}: {response.status_code}"))
            app_logs("error", (f"Response: {response.text}"))
            resp = {'error' : True, 'data' : response.json()}
            return resp
        
    async def edit_template(self, data:str, template_id):
        """
        Asynchronously sends a template message to a WhatsApp user. Templates can be:
            1. Text template
            2. Media based template
            3. Interactive template
        You can customize the template message by passing a dictionary of components.
        Find available components in the documentation:
        https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates

        Args:
            template (str): Template name to be sent to the user.
            recipient_id (str): Phone number of the user with country code without +.
            components (list): List of components to be sent to the user.
            lang (str): Language of the template message, default is "en_US".

        Example:
            >>> from whatsapp import WhatsApp
            >>> whatsapp = WhatsApp(token, phone_number_id)
            >>> await whatsapp.send_template("hello_world", "5511999999999", components=[{"type": "header", "parameters": [{"type": "text", "text": "Header Text"}]}], lang="en_US")
        """
        
        resp = {'error' : False, 'data' : None}
        
        async with httpx.AsyncClient(timeout=60) as client:
            url = f"{self.base_url}/{template_id}"
            app_logs("info", (f"editing template {url}"))
            response = await client.post(url, headers=self.headers, json=data)
        
        if response.status_code == 200:
            resp = {'error' : False, 'data' : response.json()}
            return resp
        else:
            app_logs("info", (f"editing Template {self.wb_account_id}: {response.status_code}"))
            app_logs("error", (f"Response: {response.text}"))
            resp = {'error' : True, 'data' : response.json()}
            return resp
        
    async def refresh_accesstoken(self, data):
        resp = {'error' : False, 'data' : None}
        url = f"https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id={data['data'].app_id}&client_secret={data['data'].app_secret}&fb_exchange_token={data['data'].access_token}"
        #url = f"https://graph.facebook.com/v20.0/oauth/access_token?grant_type=client_credentials&client_id={data['data'].app_id}&client_secret={data['data'].app_secret}"
        
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.get(url)

        if response.status_code == 200:
            resp = {'error' : False, 'data' : response.json()}
            return resp
        else:
            app_logs("info", (f"refresh token {self.wb_account_id}: {response.status_code}"))
            app_logs("error", (f"Response: {response.text}"))
            resp = {'error' : True, 'data' : response.json()}
            return resp
        
    async def subscribeApps(self, data):
        resp = {'error' : False, 'data' : None}
        subscribe_url = f"https://graph.facebook.com/{data['data'].message_base_version}/{data['data'].waba_id}/subscribed_apps"
    
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(subscribe_url, headers=self.media_headers)

        if response.status_code == 200:
            resp = {'error' : False, 'data' : response.json()}
            app_logs("info", (f"WABA subscribed successfully : {response.json()}"))
            return resp
        else:
            app_logs("error", (f"WABA subscribed failed : {response.json()}"))
            resp = {'error' : True, 'data' : response.json()}
            return resp
        
    async def subscribeCallBackUrl(self, data, callbackurl):

        resp = {'error' : False, 'data' : None}
        subscribe_url = f"https://graph.facebook.com/{data['data'].message_base_version}/{data['data'].app_id}/subscriptions"
    
        setup_payload = {
            "object": "whatsapp_business_account",
            "callback_url": callbackurl,
            "verify_token": f"{data['data'].webhook_verify_token}",
            "fields": f"{data['data'].subscribed_fields}", 
            "access_token": f"{data['data'].app_id}|{data['data'].app_secret}"
            }
        
        async with httpx.AsyncClient(timeout=self.timeout_settings) as client:
            response = await client.post(subscribe_url, json=setup_payload)

        if response.status_code == 200:
            resp = {'error' : False, 'data' : response.json()}
            app_logs("info", (f"Call Back URL subscribed successfully : {response.json()}"))
            return resp
        else:
            app_logs("error", (f"Call Back URL subscribed failed : {response.json()} : 'inputData' : {setup_payload}"))
            resp = {'error' : True, 'data' : response.json(), 'inputData' : setup_payload}
            return resp
        
    def is_status(self, data: dict) -> bool:
        """Checks if the webhook data is a status update (sent, delivered, read, failed)."""
        val = self.preprocess(data)
        return "statuses" in val
    def get_status(self, data: dict) -> bool:
        """Checks if the webhook data is a status update (sent, delivered, read, failed)."""
        val = self.preprocess(data)
        if isinstance(val, dict) and "statuses" in val and len(val["statuses"]) > 0:
            return val["statuses"][0]
        return None
