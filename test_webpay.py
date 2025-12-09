from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions

options = WebpayOptions(
    commerce_code="597055555532",
    api_key="579B532A489C3DEB43A96A9E0A1604A7",
    integration_type="INTEGRATION"
)

tx = Transaction(options)

try:
    response = tx.create(
        buy_order="test123",
        session_id="testsession",
        amount=1000,
        return_url="http://localhost:8000/webpay/retorno/"
    )
    print(response)
except Exception as e:
    print("ERROR:", e)