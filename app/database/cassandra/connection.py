from cassandra.cluster import Cluster, Session

from app.config.settings import settings


class CassandraConnection:
    def __init__(self):
        self.cluster : Cluster | None = None
        self.session : Session | None = None

    def connect(self)-> None:
        self.cluster = Cluster(
            contact_points=[settings.cassandra_host],
            port=settings.cassandra_port,
        )
        self.session = self.cluster.connect()

    def close(self)-> None:
        if self.session:
            self.session.shutdown()
            self.session = None
        if self.cluster:
            self.cluster.shutdown()
            self.cluster = None


    def get_session(self)-> Session:
        if not self.session:
            raise RuntimeError("Cassandra session is not established. Call connect() first.")
        return self.session

cassandra_connection = CassandraConnection()
