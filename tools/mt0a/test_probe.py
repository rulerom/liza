import socket
import unittest
from probe import Dispatcher, shared, reuseport

class Ownership(unittest.TestCase):
    def test_full_closes_rejected_not_published(self):
        d=Dispatcher(1,1);a,b=socket.socketpair();c,e=socket.socketpair()
        try:
            self.assertTrue(d.submit(a));self.assertFalse(d.submit(c));self.assertEqual(c.fileno(),-1)
            self.assertIs(d.queues[0].get_nowait(),a);d.queues[0].task_done()
            a.sendall(b'A');self.assertEqual(b.recv(1),b'A');a.close()
        finally:b.close();e.close();d.discard_pending()
    def test_cancel_closes_all_published(self):
        d=Dispatcher(1,2);a,b=socket.socketpair();c,e=socket.socketpair()
        try:
            self.assertTrue(d.submit(a));self.assertTrue(d.submit(c));d.discard_pending()
            self.assertEqual(a.fileno(),-1);self.assertEqual(c.fileno(),-1)
            self.assertEqual(b.recv(1),b'');self.assertEqual(e.recv(1),b'')
        finally:b.close();e.close()
    def test_shared_routes_and_closes(self):
        r=shared(4,32,32);self.assertEqual(r['status'],'passed');self.assertEqual(r['delivered'],[8]*4);self.assertEqual(r['refused'],0)
    def test_reuseport_report(self):
        r=reuseport(2,16);self.assertIn(r['status'],('passed','unsupported'))
        if r['status']=='passed':self.assertEqual(sum(r['delivered']),16)

if __name__=='__main__':unittest.main()
