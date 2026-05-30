class SmartConnect:
    """Minimal SmartConnect stub for offline unit tests only.

    Do not use for production. Install smartapi-python>=1.5.5 instead.
    Enable only when BALANCEWHEEL_USE_SMARTAPI_SHIM=1 (e.g. local pytest without SDK).
    """

    def __init__(self, *args, **kwargs):
        self.connected = False

    def generateSession(self, clientCode=None, password=None, totp=None, **kwargs):
        self.connected = True
        return {"status": True, "data": {"jwtToken": "TEST", "refreshToken": "TEST", "feedToken": "TEST"}}

    def placeOrder(self, *args, **kwargs):
        return {"status": "success", "orderId": "TEST_ORDER_12345"}

    def logout(self):
        self.connected = False
        return True

    def setAccessToken(self, token):
        pass

    def setRefreshToken(self, token):
        pass

    def setFeedToken(self, token):
        pass
