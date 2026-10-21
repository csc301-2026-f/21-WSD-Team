from flask import Flask, jsonify, request
from .response import success_response, fail_response


def create_http_api(core_service):
    http_api= Flask(__name__)

    @http_api.get("/api/v1/devices")
    def get_all_devices():
        all_devices = core_service.get_devices()
        response = success_response(all_devices)
        return jsonify(response)

    @http_api.get("/api/v1/metrics/latest")
    def get_all_device_metrics():
        all_device_metrics = core_service.get_current_device_metrics()
        response = success_response(all_device_metrics)
        return jsonify(response)

    @http_api.get("/api/v1/processes/latest")
    def get_all_process_metrics():
        all_process_metrics = core_service.get_current_process_activity()
        response = success_response(all_process_metrics)
        return jsonify(response)

    @http_api.get("/api/v1/recommendations")
    def get_all_recommendations():
        mode = request.args.get("mode")
        all_recommendations = core_service.get_recommendations(mode)
        response = success_response(all_recommendations)
        return jsonify(response)

    @http_api.post("/api/v1/recommendations/refresh")
    def refresh_recommendation():
        recommendations = core_service.refresh_recommendation()
        response = success_response(recommendations)
        return jsonify(response)

    @http_api.get("/api/v1/capabilities")
    def get_capabilities():
        capabilities = core_service.get_capabilities()
        response = success_response(capabilities)
        return jsonify(response)

    @http_api.errorhandler(404)
    def handle_not_found(error):
        response = fail_response("NOT_FOUND", "Endpoint Not Found")
        return jsonify(response), 404

    @http_api.errorhandler(Exception)
    def handle_core_error(error):
        response = fail_response("CORE_ERROR", "Internal Server Error")
        return jsonify(response), 500

    return http_api