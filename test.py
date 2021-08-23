import requests
import json
import unittest

API_BASE = "http://127.0.0.1:8000/api/v1"


class TestLoanPayment(unittest.TestCase):
    def test_first_upload_of_file_201(self):
        """
        Assuming that the connection between web app and elastic search is maintained
        """
        with open('./test_files/single_line.json', 'rb') as fp:
            response = requests.post(API_BASE + "/upload/", files={'file': fp})
            message = response.json()['message']
            self.assertEqual(message, "File is indexed", "Valid file should be indexed the first upload")
            self.assertTrue(response.status_code, 201)

    def test_second_upload_of_same_file_400(self):
        """
        Assuming that the connection between web app and elastic search is maintained
        """
        with open('./test_files/single_line.json', 'rb') as fp:
            response = requests.post(API_BASE + "/upload/", files={'file': fp})
            message = response.json()['message']
            self.assertEqual(message, "File already exists", "Valid file cannot be indexed the second upload")
            self.assertTrue(response.status_code, 400)

    def test_multi_line_files_accepted_200(self):
        """
        Assuming that the connection between web app and elastic search is maintained
        """
        with open('./test_files/multi_lines.json', 'rb') as fp:
            response = requests.post(API_BASE + "/upload/", files={'file': fp})
            message = response.json()['message']
            self.assertEqual(message, "File is indexed", "Multi-line json files can be indexed.")
            self.assertTrue(response.status_code, 200)

    def test_upload_file_no_extension_400(self):
        """
        Assuming that the connection between web app and elastic search is maintained
        """
        with open('./test_files/no_ext', 'rb') as fp:
            response = requests.post(API_BASE + "/upload/", files={'file': fp})
            message = response.json()['message']
            self.assertEqual(message, "Files should have extensions", "Currently, doesn't allow upload of files "
                                                                      "without extension")
            self.assertTrue(response.status_code, 400)

    def test_upload_file_unsupported_extension_400(self):
        """
        Assuming that the connection between web app and elastic search is maintained
        """
        with open('./test_files/pdf.pdf', 'rb') as fp:
            response = requests.post(API_BASE + "/upload/", files={'file': fp})
            message = response.json()['message']
            self.assertEqual(message, "The only allowed file extension is .json", "Currently, only .json accepted.")
            self.assertTrue(response.status_code, 400)

    def test_search_returns_200(self):
        """
        Assuming the above file is indexed, search returns 200
        """
        query = {'query': {'multi_match': {'query': "the", 'fields': ['*']}},
                 'from': 0 * 10, 'size': 10}
        query = json.dumps(query)
        response = requests.get(API_BASE + "/search/", data=query,
                                headers={'content-type': 'application/json'})
        self.assertTrue(response.status_code, 400)

    def test_from_size_search_returns_200_(self):
        """
        from and size used for pagination are optional
        """
        query = {'query': {'multi_match': {'query': "thedfadsfadfa", 'fields': ['*']}},
                 'from': 0 * 10, 'size': 10}
        query = json.dumps(query)
        response = requests.get(API_BASE + "/search/", data=query,
                                headers={'content-type': 'application/json'})
        self.assertTrue(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
