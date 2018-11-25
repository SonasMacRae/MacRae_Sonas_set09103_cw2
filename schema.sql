DROP TABLE if EXISTS users;
DROP TABLE if EXISTS jokes;

CREATE TABLE users (
	username text,
	password text
);

CREATE TABLE jokes (
	joke text,
	author text
);
