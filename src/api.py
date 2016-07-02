from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import LegacyApplicationClient


class CybApi:
    _base_url = "https://internt.cyb.no/"

    def __init__(self, username, password, client_id, client_secret):
        self.username = username
        self.password = password
        self.client_id = client_id
        self.client_secret = client_secret

        # Get a token via the Resource Owner Password Credential Grant OAuth2 API
        oauth = OAuth2Session(client=LegacyApplicationClient(client_id=client_id))
        self._token = oauth.fetch_token(
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


    def get_card_owner(self, card_id):
        print(card_id)
        # FIXME: The card_id is not the ID we expect.

        url = self._base_url + "api/core/nfc"
        params = {"format": "json", "card_uid": card_id}

        request = self._client.get(url, params=params)
        json = request.json()

        if not json:
            return ("", "")

        return (json["user"]["username"], json["user"]["realname"])


    def get_voucher_balance(self, username):
        # FIXME: This should be done in the internsystem!
        url = self._base_url + "api/voucher/wallets"
        params = {"format": "json", "user": username}
        
        request = self._client.get(url, params=params)
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

        request = self._client.post(url, data=data)

        if request.status_code == 201:
            return True
        elif request.status_code == 402:
            return False
        else:
            print(str(request.status_code) + "\n" + str(request.content))
