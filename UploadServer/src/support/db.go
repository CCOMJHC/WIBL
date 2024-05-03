package support

import (
	"database/sql"
	"encoding/base64"
	"errors"

	_ "github.com/mattn/go-sqlite3"
	"golang.org/x/crypto/bcrypt"
)

type DBConnection struct {
	dbfile string
	db     *sql.DB
}

func NewDatabase(dbfile string) (DBConnection, error) {
	var rtn DBConnection
	var err error

	rtn.dbfile = dbfile
	rtn.db, err = sql.Open("sqlite3", dbfile)
	if err != nil {
		Errorf("DB: Failed to open SQLite database in %s: %v", dbfile, err)
		return DBConnection{}, err
	}
	return rtn, nil
}

func (database DBConnection) Setup() error {
	if database.db == nil {
		Errorf("DB: Connection is closed!")
		return errors.New("database connection closed")
	}
	const create string = `
		CREATE TABLE IF NOT EXISTS loggers (
			name TEXT NOT NULL PRIMARY KEY,
			hash TEXT NOT NULL
		);`
	if _, err := database.db.Exec(create); err != nil {
		Errorf("DB: Failed to create logger table in database %s: %v", database.dbfile, err)
		return err
	}
	return nil
}

func (database DBConnection) LookupLogger(logger string) ([]byte, error) {
	if database.db == nil {
		Errorf("DB: Connection is closed!")
		return []byte{}, errors.New("database connection closed")
	}
	const query string = `
		SELECT hash FROM loggers WHERE name = ?;`
	row := database.db.QueryRow(query, logger)
	var err error
	var encodedPassword string
	if err = row.Scan(&encodedPassword); err != nil {
		Infof("DB: Logger %s not found in database.", logger)
		return []byte{}, err
	}
	hashedPassword, err := base64.StdEncoding.DecodeString(encodedPassword)
	if err != nil {
		Errorf("DB: failed to decode base64 encoded password from database (%v)\n", err)
		return []byte{}, err
	}
	return hashedPassword, nil
}

func (database DBConnection) ValidateLogger(logger string, password string) error {
	hashedPassword, err := database.LookupLogger(logger)
	if err != nil {
		return err
	}
	return bcrypt.CompareHashAndPassword(hashedPassword, []byte(password))
}

func GeneratePasswordHash(password string) ([]byte, error) {
	hashed, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		Errorf("DB: failed to generate password has from plaintext.\n")
		return []byte{}, err
	}
	return hashed, nil
}

func GenerateStorablePassword(password string) (string, error) {
	hashed, err := GeneratePasswordHash(password)
	if err != nil {
		return "", err
	}
	storable := base64.StdEncoding.EncodeToString(hashed)
	return storable, nil
}

func (database DBConnection) InsertLogger(logger string, password string) error {
	const insert string = `
		INSERT INTO loggers VALUES(?,?);`
	storablePassword, err := GenerateStorablePassword(password)
	if err != nil {
		return err
	}
	_, err = database.db.Exec(insert, logger, storablePassword)
	if err != nil {
		Errorf("DB: failed to insert logger %s into database (%v).\n", logger, err)
		return err
	}
	return nil
}
