import socket
import unittest
from unittest.mock import patch
import webtools


def addr(ip):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip, 443))]


class WebTests(unittest.TestCase):
    def test_blocks_private_loopback_and_metadata(self):
        for ip in ('127.0.0.1','10.0.0.1','192.168.1.1','169.254.169.254','100.64.0.1','0.0.0.0','224.0.0.1'):
            with patch.object(socket, 'getaddrinfo', return_value=addr(ip)):
                with self.assertRaises(ValueError):
                    webtools.public_target('https://example.com')

    def test_blocks_protocol_credentials_and_nonstandard_ports(self):
        for url in ('file:///etc/passwd','ftp://example.com','https://user:pass@example.com','http://example.com:8765'):
            with self.assertRaises(ValueError):
                webtools.public_target(url)

    def test_pins_checked_public_address(self):
        with patch.object(socket, 'getaddrinfo', return_value=addr('8.8.8.8')):
            p, host, port, target = webtools.public_target('https://example.com/page')
        self.assertEqual(target, '8.8.8.8')
        self.assertEqual(host, 'example.com')
        self.assertEqual(port, 443)

    def test_search_parser_and_failures(self):
        html = '<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com">Example <b>title</b></a>'
        with patch.object(webtools, 'fetch', return_value=('https://duckduckgo.com', html)):
            result = webtools.search('test')
        self.assertEqual(result['results'][0], {'title':'Example title','url':'https://example.com'})
        with patch.object(webtools, 'fetch', return_value=('https://duckduckgo.com', 'Captcha')):
            with self.assertRaises(RuntimeError):
                webtools.search('test')

    def test_page_text_omits_scripts_and_bounds_content(self):
        html = '<title>Title</title><script>secret code</script><p>Hello world</p><style>css</style>'
        with patch.object(webtools, 'fetch', return_value=('https://example.com', html)):
            result = webtools.read_page('https://example.com')
        self.assertEqual(result['title'], 'Title')
        self.assertIn('Hello world', result['text'])
        self.assertNotIn('secret code', result['text'])
        self.assertNotIn('css', result['text'])

    def test_redirect_to_private_target_is_blocked(self):
        response = unittest.mock.Mock()
        response.status = 302
        response.getheader.return_value = 'http://127.0.0.1/'
        connection = unittest.mock.Mock()
        connection.getresponse.return_value = response
        with patch.object(socket, 'getaddrinfo', side_effect=[addr('8.8.8.8'),addr('127.0.0.1')]), patch.object(webtools, 'PinnedHTTPS', return_value=connection):
            with self.assertRaises(ValueError):
                webtools.fetch('https://example.com')
        connection.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
