package main

import (
	"deon-api-server/internal/router"
	"log"
	"net/http"
	"time"
)

func main() {
	r := router.New()
	addr := ":28980"
	srv := &http.Server{
		Addr:         addr,
		Handler:      r,
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 10 * time.Second,
	}

	log.Printf("API server listening on %s\n", addr)
	log.Fatal(srv.ListenAndServe())
}
