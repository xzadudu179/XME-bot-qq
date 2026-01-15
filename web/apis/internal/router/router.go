package router

import (
	"net/http"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"

	"deon-api-server/internal/handler"
	deonMiddleware "deon-api-server/internal/middleware"
)

func New() http.Handler {
	r := chi.NewRouter()

	// 通用中间件
	r.Use(middleware.RequestID)
	r.Use(middleware.Recoverer)
	r.Use(deonMiddleware.Logger)

	// 路由
	r.Get("/health", handler.HealthCheck)

	return r
}
