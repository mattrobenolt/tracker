from bencode import bencode
from urlparse import parse_qs
from collections import namedtuple
from struct import pack, unpack
import socket
import importlib
import settings


ANNOUNCE_PATH = settings.ANNOUNCE_PATH
ANNOUNCE_INTERVAL = settings.ANNOUNCE_INTERVAL

PLAIN_TEXT_HEADERS = ('Server', 'Candid Camera 1.0'), ('Content-Type', 'text/plain')
STATUS_404 = '404 Not Found'
STATUS_200 = '200 OK'

REQUIRED_KEYS = frozenset(['info_hash', 'peer_id', 'port', 'uploaded', 'downloaded', 'left'])

# Load backend
STORAGE_BACKEND = settings.STORAGE_BACKEND.split('.')
cls = STORAGE_BACKEND.pop()
module = importlib.import_module('.'.join(STORAGE_BACKEND))
storage = getattr(module, cls)(**settings.STORAGE_BACKEND_OPTIONS)


def make_failure():
    "Generic bad request failure"
    return ['d14:failure reason18:Malformed announcee']

def make_peers(peers, compact=False):
    "Generate a list of peers in an acceptable format for the interwebz"
    a = '' if compact else []
    for peer in peers:
        if compact:
            # I don't even know what I'm doing
            a += pack('LH', unpack('>L', socket.inet_aton(peer.ip))[0], peer.port)
        else:
            a.append({
                'id': peer.id,
                'ip': peer.ip,
                'port': peer.port
            })
    return a

def application(env, start_response):
    if env['PATH_INFO'] != ANNOUNCE_PATH:
        start_response(STATUS_404, PLAIN_TEXT_HEADERS)
        return ['404']

    # Requests MUST be GET
    if env['REQUEST_METHOD'] != 'GET':
        return make_failure()

    qs = parse_qs(env['QUERY_STRING'])

    # Make sure that all of the required keys are present
    if not REQUIRED_KEYS.issubset(set(qs.keys())):
        return make_failure()

    try:
        peer_id = qs['peer_id'][0]
        torrent_id = qs['info_hash'][0].encode('hex')
        port = int(qs['port'][0])
        uploaded = int(qs['uploaded'][0])
        downloaded = int(qs['downloaded'][0])
        left = int(qs['left'][0])
        ip = env.get('HTTP_X_FORWARDED_FOR', env['REMOTE_ADDR'])
        numwant = int(qs.get('numwant', [50])[0])  # Optional
        event = qs.get('event')  # Optional
        compact = bool(int(qs.get('compact', [0])[0]))  # Optional
    except (ValueError, KeyError) as e:
        return make_failure()

    storage.announce(torrent_id, peer_id, ip, port, uploaded, downloaded, left)

    total_peers = storage.total_peers(torrent_id)
    print "Total peers:", total_peers

    seeders = storage.seeders(torrent_id)
    print "Seeders:", seeders

    response = [bencode({
        'interval': ANNOUNCE_INTERVAL + min(600, seeders),  # distrbute announces according to Ocelot
        'min interval': ANNOUNCE_INTERVAL,
        'peers': make_peers(storage.peers(torrent_id, numwant), compact=compact),
        'complete': seeders,
        'downloaded': storage.downloaded(torrent_id),
        'incomplete': total_peers - seeders
    })]

    print "Torrent:", torrent_id
    print "Peer id:", peer_id
    print "Response:", response
    start_response(STATUS_200, PLAIN_TEXT_HEADERS)
    return response

if __name__ == '__main__':
    from gevent import monkey; monkey.patch_all()
    from gevent.pywsgi import WSGIServer
    import sys
    try:
        print "Running on http://0.0.0.0:{0}/".format(sys.argv[1])
        WSGIServer(('', int(sys.argv[1])), application).serve_forever()
    except KeyboardInterrupt:
        pass
