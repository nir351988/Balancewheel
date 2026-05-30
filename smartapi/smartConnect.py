class SmartConnect:
    """Minimal SmartConnect shim for unit tests only.

    This stub implements the smallest surface area needed so unit tests that import
    SmartConnect won't fail during import. It intentionally does not attempt to
    contact any external API.

    Production: install smartapi-python>=1.5.5 from requirements.txt.
    See docs/VERIFICATION.md.
    """

    def __init__(self, *args, **kwargs):
        self.connected = False

    def generateSession(self):
        self.connected = True
        return {"status": "success"}

    def placeOrder(self, *args, **kwargs):
        # Return a fake order response structure similar to what the real SDK might return
        return {"status": "success", "orderId": "TEST_ORDER_12345"}

    def logout(self):
        self.connected = False
        return True
