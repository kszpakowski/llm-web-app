import zeep

class GtcClient:
    def __init__(self):
        wsdl = "https://gtc.nn.pl/gtc/services/GtcServiceHttpPort?wsdl"
        self.client = zeep.Client(wsdl=wsdl)

    def get_all_documents_metadata(self):
        return self.client.service.getAllGtcDocuments().body["return"]

    def get_doc_body(self, doc_id):
        return self.client.service.getGtcDocumentBody(doc_id).body["return"]
