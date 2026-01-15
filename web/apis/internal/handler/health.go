package handler

import (
	"net/http"

	"deon-api-server/internal/service"
	"deon-api-server/pkg/response"
)

func HealthCheck(w http.ResponseWriter, r *http.Request) {
	status := service.HealthStatus()
	response.JSON(w, http.StatusOK, status)
}
