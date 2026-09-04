package repository

import (
	"database/sql"

	_ "github.com/mattn/go-sqlite3"
)

type Executor interface {
	Exec(query string, args ...any) (sql.Result, error)
	Query(query string, args ...any) (*sql.Rows, error)
	QueryRow(query string, args ...any) *sql.Row
}

func (d *database) ExecTx(
	query string,
	args ...any,
) error {
	return d.WithTx(func(ex Executor) error {
		_, err := ex.Exec(query, args...)
		return err
	})
}

func (d *database) Exec(
	query string,
	args ...any,
) (sql.Result, error) {
	return d.db.Exec(query, args...)
}

func (d *database) Query(
	query string,
	args ...any,
) (*sql.Rows, error) {
	return d.db.Query(query, args...)
}

func (d *database) QueryRow(
	query string,
	args ...any,
) *sql.Row {
	return d.db.QueryRow(query, args...)
}

type database struct {
	db *sql.DB
}

type DBFunc func(*sql.Tx) error

func (d *database) WithTx(fn func(Executor) error) error {
	tx, err := d.db.Begin()
	if err != nil {
		return err
	}

	if err := fn(tx); err != nil {
		err1 := tx.Rollback()
		if err1 != nil {
			return err1
		}
		return err
	}
	return tx.Commit()
}

func newDatabase() (*database, error) {
	db, err := sql.Open("sqlite3", "./data.db")
	if err != nil {
		return nil, err
	}
	db.SetMaxOpenConns(1)
	db.SetMaxIdleConns(1)

	if err := db.Ping(); err != nil {
		return nil, err
	}

	return &database{db: db}, nil
}
