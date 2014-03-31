import unittest
from unittest import mock

import asyncio
import aiohttp
import email
from aiorest import RESTServer, Request
import json

from test.support import find_unused_port


def func_POST(id, request):
    assert id == '123', id
    assert request.json_body == {'q': 'val'}, request.json_body
    return {'success': True}


def func_GET(id: int, req):
    assert id == 123, id
    assert req.json_body is None, req.json_body
    return {'success': True}


def func_GET2(id: int, req):
    assert id == 123, id
    assert req.json_body is None, req.json_body
    assert req.version == (1, 1), req.version
    assert req.method == 'GET', req.method
    assert req.host == 'localhost', req.host
    assert req.host_url == 'http://localhost', req.host_url
    assert req.path_qs == '/post/123/2?a=1&b=2', req.path_qs
    assert req.path == '/post/123/2', req.path
    assert req.path_url == 'http://localhost/post/123/2', req.path_url
    assert req.url == 'http://localhost/post/123/2?a=1&b=2', req.url
    assert req.query_string == 'a=1&b=2', req.query_string
    assert req.args['a'] == '1', req.arg
    assert req.args['b'] == '2', req.arg
    return {'success': True, 'args': list(req.args)}


class RouterTests(unittest.TestCase):

    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)
        self.server = RESTServer(debug=True, keep_alive=75,
                                 hostname='localhost', loop=self.loop)
        self.server.add_url('POST', '/post/{id}', func_POST, use_request=True)
        self.server.add_url('GET', '/post/{id}', func_GET, use_request='req')
        self.server.add_url('GET', '/post/{id}/2', func_GET2, use_request='req')

    def tearDown(self):
        self.loop.close()

    def test_simple_POST(self):
        port = find_unused_port()

        svr = self.loop.run_until_complete(self.loop.create_server(
            lambda: self.server,
            'localhost', port))
        url = 'http://localhost:{}/post/123'.format(port)

        def query():
            response = yield from aiohttp.request(
                'POST', url,
                data=json.dumps({'q': 'val'}).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                loop=self.loop)
            self.assertEqual(200, response.status)
            data = yield from response.read()
            self.assertEqual(b'{"success": true}', data)

        self.loop.run_until_complete(query())

        svr.close()
        self.loop.run_until_complete(svr.wait_closed())

    def test_simple_GET(self):
        port = find_unused_port()

        svr = self.loop.run_until_complete(self.loop.create_server(
            lambda: self.server,
            'localhost', port))
        url = 'http://localhost:{}/post/123'.format(port)

        def query():
            response = yield from aiohttp.request('GET', url, loop=self.loop)
            self.assertEqual(200, response.status)
            data = yield from response.read()
            self.assertEqual(b'{"success": true}', data)

        self.loop.run_until_complete(query())

        svr.close()
        self.loop.run_until_complete(svr.wait_closed())

    def test_GET_with_query_string(self):
        port = find_unused_port()

        svr = self.loop.run_until_complete(self.loop.create_server(
            lambda: self.server,
            'localhost', port))
        url = 'http://localhost:{}/post/123/2?a=1&b=2'.format(port)

        def query():
            response = yield from aiohttp.request('GET', url, loop=self.loop)
            self.assertEqual(200, response.status)
            data = yield from response.read()
            dct = json.loads(data.decode('utf-8'))
            self.assertEqual({'success': True,
                              'args': [['a', '1'], ['b', '2']],
                              }, dct)

        self.loop.run_until_complete(query())

        svr.close()
        self.loop.run_until_complete(svr.wait_closed())