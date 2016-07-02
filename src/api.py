from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import LegacyApplicationClient


class CybApi:
    _base_url = "https://tomcat.mrow.me:8080/"

    def __init__(self, username, password, client_id, client_secret):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret

        # Get a token via the Resource Owner Password Credential Grant OAuth2 API
        oauth = OAuth2Session(client=LegacyApplicationClient(client_id=client_id))
        self._token = oauth.fetch_token(verify=False,
                token_url=self._base_url + "o/token/",
                username=username, password=password,
                client_id=client_id, client_secret=client_secret
        )
        # Make a client for connecting to the API.
        self._client = OAuth2Session(
                client_id,
                token = self._token,
                auto_refresh_url=self._base_url + "o/token/",
                auto_refresh_kwargs={
                    "client_id": client_id,
                    "client_secret": client_secret
                },
                token_updater=self._token_updater
        )
        
    def _token_updater(self, token):
        self._token = token


    def get_user(self, username):
        url = self._base_url + "api/core/users/" + username

        request = self._client.get(url, verify=False)
        json = request.json()

        return json

    def get_card_info(self, card_uid):
        url = self._base_url + "api/core/nfc"
        params = {"format": "json", "card_uid": card_uid}

        request = self._client.get(url, params=params, verify=False)
        json = request.json()

        # If there is no JSON, the card does not exist in the db.
        if not json:
            return (None, None)
        else:
            json = json[0] # For some reason it returns a dict within a list...

        if not json["user"]:
            return ("", json["intern"])
        return (json["user"]["username"], json["intern"])

    def register_card(self, card_uid, username="", is_intern=False, comment=""):
        url = self._base_url + "api/core/nfc"
        data = {"card_uid": card_uid, "user": username, "intern": is_intern, "comment": comment}

        request = self._client.post(url, data=data, verify=False)

        if request.status_code == 201:
            return True
        else:
            return False

    def get_voucher_balance(self, username):
        # FIXME: This should be done in the internsystem!
        url = self._base_url + "api/voucher/wallets"
        params = {"format": "json", "user": username}
        
        request = self._client.get(url, params=params, verify=False)
        json = request.json()

        # A user can have multiple wallets due to multiple semesters
        balance = 0
        for wallet in json:
            if wallet["is_valid"]:
                balance += float(wallet["cached_balance"])

        return balance

    def get_coffee_voucher_balance(self, card_uid):
        # TODO: Not implemented in internsystem yet
        return 0

    def use_vouchers(self, username, amount):
        url = self._base_url + "api/voucher/users/" + username + "/use_vouchers"
        data = {"vouchers": amount}

        request = self._client.post(url, data=data, verify=False)

        if request.status_code == 201:
            return True
        elif request.status_code == 402:
            return False
        else:
            print(str(request.status_code) + "\n" + str(request.content))
