# SPDX-FileCopyrightText: 2026 Wise Storage Director contributors
# SPDX-License-Identifier: GPL-3.0-only
from flask import Flask, jsonify, request
from .response import success_response, fail_response
from datetime import datetime


def is_valid_utc(value):
    """
    Check whether a value is a valid UTC ISO 8601 timestamp.
    """
    try:
        time = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return time.tzinfo is not None and time.utcoffset().total_seconds() == 0
    except (ValueError, AttributeError):
        return False

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

    @http_api.get("/api/v1/processes/history")
    def get_process_history():
        process_instance_id = request.args.get("process_instance_id")
        start_utc = request.args.get("start_utc")
        end_utc = request.args.get("end_utc")
        bucket_seconds = request.args.get("bucket_seconds")
        if process_instance_id is None or start_utc is None or end_utc is None:
            response = fail_response("INVALID_REQUEST", "Missing required parameter")
            return jsonify(response), 400
        if not is_valid_utc(start_utc) or not is_valid_utc(end_utc):
            response = fail_response("INVALID_REQUEST", "Invalid UTC time format")
            return jsonify(response), 400
        start_time = datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(end_utc.replace("Z", "+00:00"))
        if start_time > end_time:
            response = fail_response("INVALID_REQUEST", "Invalid time range")
            return jsonify(response), 400
        if bucket_seconds is not None:
            try:
                bucket_seconds = int(bucket_seconds)
            except ValueError:
                response = fail_response("INVALID_REQUEST", "Invalid bucket seconds")
                return jsonify(response), 400
            if bucket_seconds <= 0:
                response = fail_response("INVALID_REQUEST", "Invalid bucket seconds")
                return jsonify(response), 400
        process_history = core_service.get_historical_process_activity(
            [process_instance_id],
            start_utc,
            end_utc,
            bucket_seconds)
        response = success_response(process_history)
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