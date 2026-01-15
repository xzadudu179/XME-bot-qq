package service

type HealthResponse struct {
	Status string `json:"status"`
}

func HealthStatus() HealthResponse {
	return HealthResponse{
		Status: "ok",
	}
}
