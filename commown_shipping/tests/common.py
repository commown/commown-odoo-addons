import os.path as osp

HERE = osp.dirname(__file__)

BASE_URL = "https://ws.colissimo.fr/sls-ws"


def mock_colissimo_ok(mocker):
    with open(osp.join(HERE, "fake_label_response.txt"), "rb") as fobj:
        body = fobj.read()

    headers = {
        "Content-Transfer-Encoding": "binary",
        "Content-Type": " ".join(
            [
                "multipart/related;",
                'type="application/xop+xml";',
                'boundary="uuid:ad5b92e7-6d39-45e0-8c94-0a5a0f2611fa";',
                'start="<root.message@cxf.apache.org>";',
            ]
        ),
    }

    mocker.post(
        BASE_URL + "/SlsServiceWS/2.0?wsdl",
        content=body,
        headers=headers,
        # real_http=True,
    )
