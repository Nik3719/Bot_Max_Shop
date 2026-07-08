CREATE_USERS_TABLE = """
create table if not exists users (
    id integer primary key autoincrement,
    max_user_id integer unique not null,
    full_name text not null,
    phone text unique not null,
    registered_at datetime default current_timestamp
);
"""

CREATE_PRODUCTS_TABLE = """
create table if not exists products (
    product_id text primary key,
    name text not null,
    description text,
    price integer not null,
    category text,
    photo_url text,
    is_active integer default 1
);
"""

CREATE_ORDERS_TABLE = """
create table if not exists orders (
    id integer primary key autoincrement,
    max_user_id integer not null,
    product_id text not null,
    comment text,
    status text default 'new',
    created_at datetime default current_timestamp
);
"""

CREATE_SYNC_LOG_TABLE = """
create table if not exists sync_log (
    id integer primary key autoincrement,
    started_at datetime default current_timestamp,
    finished_at datetime,
    status text not null,
    initiator_id integer,
    inserted integer default 0,
    updated integer default 0,
    deactivated integer default 0
);
"""

SELECT_USER_BY_ID = "select max_user_id, full_name, phone from users where max_user_id=?;"
SELECT_USER_ID_BY_PHONE = "select id from users where phone=?;"
INSERT_USER = "insert into users (max_user_id, full_name, phone) values (?, ?, ?);"

# Products
UPSERT_PRODUCT = """
insert into products (product_id, name, description, price, category, photo_url, is_active)
values (?, ?, ?, ?, ?, ?, 1)
on conflict(product_id) do update set
    name=excluded.name,
    description=excluded.description,
    price=excluded.price,
    category=excluded.category,
    photo_url=excluded.photo_url,
    is_active=1;
"""
DEACTIVATE_PRODUCT = "update products set is_active = 0 where product_id = ?;"
SELECT_ACTIVE_PRODUCTS = "select product_id, name, description, price, category, photo_url from products where is_active = 1 order by rowid asc;"
SELECT_ACTIVE_PRODUCT_BY_ID = "select product_id, name, description, price, category, photo_url from products where product_id = ? and is_active = 1;"

# Orders
INSERT_ORDER = "insert into orders (max_user_id, product_id, comment, status) values (?, ?, ?, 'new');"
SELECT_NEW_ORDERS = """
select o.id, u.full_name, u.phone, p.name, p.price, o.status, o.created_at, o.comment
from orders o
join users u on o.max_user_id = u.max_user_id
join products p on o.product_id = p.product_id
where o.status = 'new'
order by o.created_at asc;
"""
SELECT_USER_ORDERS = """
select o.id, p.name, p.price, o.status, o.created_at
from orders o
join products p on o.product_id = p.product_id
where o.max_user_id = ?
order by o.created_at desc
limit ?;
"""
UPDATE_ORDER_STATUS = "update orders set status = ? where id = ?;"

# Stats
SELECT_USERS_COUNT = "select count(*) from users where max_user_id not in ({placeholders});"
SELECT_PRODUCTS_COUNT = "select count(*) from products where is_active = 1;"
SELECT_ORDERS_COUNT = "select count(*) from orders;"

# Sync log
INSERT_SYNC_LOG = "insert into sync_log (status, initiator_id) values (?, ?);"
UPDATE_SYNC_LOG = "update sync_log set finished_at = current_timestamp, status = ?, inserted = ?, updated = ?, deactivated = ? where id = ?;"
SELECT_LAST_SYNC = "select finished_at, status, inserted, updated, deactivated from sync_log order by id desc limit 1;"
