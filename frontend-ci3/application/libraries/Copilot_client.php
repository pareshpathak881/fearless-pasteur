<?php
defined('BASEPATH') OR exit('No direct script access allowed');

class Copilot_client {

    protected $api_url;
    protected $api_key;
    protected $timeout;

    public function __construct($params = array()) {
        $this->api_url = isset($params['copilot_api_url']) ? rtrim($params['copilot_api_url'], '/') : (getenv('COPILOT_API_URL') ?: 'http://copilot-api:8000');
        $this->api_key = isset($params['copilot_api_key']) ? $params['copilot_api_key'] : (getenv('COPILOT_API_KEY') ?: 'atlas_secret_api_key_2025');
        $this->timeout = isset($params['copilot_timeout']) ? intval($params['copilot_timeout']) : 30;
    }

    /**
     * Send chat inquiry to FastAPI backend.
     */
    public function send_query($client_id, $query, $session_id = 'default') {
        $endpoint = $this->api_url . '/chat';
        $payload = json_encode(array(
            'client_id'  => $client_id,
            'query'      => $query,
            'session_id' => $session_id
        ));

        $ch = curl_init($endpoint);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
        curl_setopt($ch, CURLOPT_TIMEOUT, $this->timeout);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'Content-Type: application/json',
            'X-API-Key: ' . $this->api_key,
            'Accept: application/json'
        ));

        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $curl_error = curl_error($ch);
        curl_close($ch);

        if ($response === false || !empty($curl_error)) {
            log_message('error', "Report Copilot cURL Failure: " . $curl_error);
            return array(
                'success' => false,
                'data' => array(
                    'answer' => "Service Unavailable: The Report Copilot backend did not respond within the {$this->timeout}-second timeout threshold. Please verify connectivity or retry your request.",
                    'citations' => array(),
                    'confidence' => 0.0,
                    'conflicts' => array(),
                    'derived_values' => array(),
                    'escalated' => true,
                    'fallback_triggered' => true
                )
            );
        }

        $decoded = json_decode($response, true);
        if ($http_code !== 200 || !$decoded) {
            log_message('error', "Report Copilot HTTP {$http_code} Response: " . $response);
            return array(
                'success' => false,
                'data' => array(
                    'answer' => "Cognitive Copilot Advisory: The service returned status code {$http_code}. " . (isset($decoded['detail']) ? $decoded['detail'] : 'Internal service fault.'),
                    'citations' => array(),
                    'confidence' => 0.0,
                    'conflicts' => array(),
                    'derived_values' => array(),
                    'escalated' => false,
                    'fallback_triggered' => true
                )
            );
        }

        return array(
            'success' => true,
            'data'    => $decoded
        );
    }

    /**
     * Fetch list of pending escalations.
     */
    public function get_escalations() {
        $endpoint = $this->api_url . '/escalations';
        $ch = curl_init($endpoint);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'X-API-Key: ' . $this->api_key,
            'Accept: application/json'
        ));

        $response = curl_exec($ch);
        curl_close($ch);

        if (!$response) {
            return array('tickets' => array());
        }

        $decoded = json_decode($response, true);
        return isset($decoded['tickets']) ? $decoded['tickets'] : array();
    }
}
