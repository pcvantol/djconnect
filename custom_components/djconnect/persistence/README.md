# DJConnect Persistence Platform

The persistence platform owns database opening, schema lifecycle, migrations,
integrity validation and transaction boundaries. It is the only component that
may create SQLite connections or resolve the private `.storage/djconnect.sqlite3`
location. Repositories may use the platform transaction boundary but never
receive a raw connection or database path.

SQLite uses WAL for concurrent readers with short serialized writes,
foreign-key enforcement, a bounded busy timeout and `synchronous=NORMAL`.
The database remains an internal backup artifact: a consistent backup must
coordinate WAL/checkpoint state; product export is never a copied database file.

Migration definitions are immutable, ordered and identity-checked. Bootstrap
runs the same chain for fresh and existing databases, validates migration
history and schema shape, and never downgrades or recreates a newer or malformed
database. This layer stores no Session, Profile, Music DNA or other product data.
