from collections import defaultdict


Peer = type('Peer', (object,), {})
Torrent = type('Torrent', (object,), {})
Progress = type('Progress', (object,), {})


class LocMem(object):
    peers_by_id = {}
    torrents_by_id = {}
    progress_by_id = {}
    progress_by_torrent = defaultdict(set)

    def announce(self, torrent_id, peer_id, peer_ip, peer_port, uploaded, downloaded, left):
        try:
            peer = self.peers_by_id[peer_id]
            print "Peer %s found in swarm" % peer_id
        except KeyError:
            peer = Peer()
            peer.id = peer_id
            peer.ip = peer_ip
            peer.port = peer_port
            peer.torrents = set()
            self.peers_by_id[peer_id] = peer
            print "Peer %s added to swarm" % peer_id

        try:
            torrent = self.torrents_by_id[torrent_id]
            print "Torrent %s found" % torrent_id
        except KeyError:
            torrent = Torrent()
            torrent.id = torrent_id
            torrent.peers = set()
            self.torrents_by_id[torrent_id] = torrent
            print "Torrent %s registered" % torrent_id

        progress_id = '{0}:{1}'.format(peer_id, torrent_id)
        try:
            progress = self.progress_by_id[progress_id]
        except KeyError:
            progress = Progress()
            progress.id = progress_id
            self.progress_by_id[progress_id] = progress

        torrent.peers.add(peer_id)
        peer.torrents.add(torrent_id)
        self.progress_by_torrent[torrent_id].add(progress)

        # Update progress
        progress.uploaded = uploaded
        progress.downloaded = downloaded
        progress.left = left

        return True  # Sure

    def total_peers(self, torrent_id):
        return len(self.torrents_by_id[torrent_id].peers)

    def seeders(self, torrent_id):
        seeders = 0
        for progress in self.progress_by_torrent[torrent_id]:
            if progress.left == 0:
                seeders += 1
        return seeders

    def leechers(self, torrent_id):
        return self.total_peers(torrent_id) - self.seeders(torrent_id)

    def peers(self, torrent_id, numwant=50):
        return [self.peers_by_id[id_] for id_ in list(self.torrents_by_id[torrent_id].peers)[:numwant]]

    def downloaded(self, torrent_id):
        return 0  # We're not keeping track of this
