<?php
defined('BASEPATH') OR exit('No direct script access allowed');

class Chat extends CI_Controller {

    public function __construct() {
        parent::__construct();
        $this->load->library('copilot_client');
        $this->load->helper(array('url', 'security', 'form'));
        // Try loading model if db configured, otherwise graceful fallback
        if (class_exists('CI_Model')) {
            $this->load->model('feedback_model');
        }
    }

    /**
     * Display the main Report Copilot portal view.
     */
    public function index() {
        $data['title'] = 'Report Copilot | Cognitive Market Research & Consulting';
        $data['clients'] = array(
            'C-01' => array('name' => 'Northwind Utilities', 'reports' => 'R-101 (Paid), R-103 (Paid), R-102 (Public)'),
            'C-02' => array('name' => 'Blue Delta Infra', 'reports' => 'R-103 (Paid), R-102 (Public)')
        );
        $data['session_id'] = uniqid('sess_', true);
        
        // Pass CSRF token info to view
        $data['csrf'] = array(
            'name' => $this->security->get_csrf_token_name(),
            'hash' => $this->security->get_csrf_hash()
        );

        $this->load->view('chat_view', $data);
    }

    /**
     * AJAX Endpoint: Process chat inquiries.
     * Enforces CSRF verification and escapes output.
     */
    public function send_message() {
        // Enforce JSON request/response
        if (!$this->input->is_ajax_request() && $this->input->method() !== 'post') {
            show_404();
            return;
        }

        $client_id = $this->security->xss_clean($this->input->post('client_id'));
        $query = $this->security->xss_clean($this->input->post('query'));
        $session_id = $this->security->xss_clean($this->input->post('session_id')) ?: 'sess_default';

        if (empty($client_id) || empty($query)) {
            $this->output
                ->set_content_type('application/json')
                ->set_status_header(400)
                ->set_output(json_encode(array(
                    'status' => 'error',
                    'message' => 'Missing required fields: client_id and query.'
                )));
            return;
        }

        // Call Python service via library
        $result = $this->copilot_client->send_query($client_id, $query, $session_id);

        // Store chat in MySQL database if available
        if (isset($this->feedback_model)) {
            try {
                $response_text = isset($result['data']['answer']) ? $result['data']['answer'] : '';
                $this->feedback_model->record_feedback($client_id, $session_id, $query, $response_text, null);
            } catch (Exception $e) {
                log_message('error', 'Feedback model database recording failed: ' . $e->getMessage());
            }
        }

        // Regenerate CSRF token hash for continuous AJAX calls
        $csrf_hash = $this->security->get_csrf_hash();

        $this->output
            ->set_content_type('application/json')
            ->set_status_header($result['success'] ? 200 : 503)
            ->set_output(json_encode(array(
                'status' => $result['success'] ? 'success' : 'fallback',
                'data' => $result['data'],
                'csrf_hash' => $csrf_hash
            )));
    }

    /**
     * AJAX Endpoint: Submit Thumbs-Up / Thumbs-Down rating.
     */
    public function feedback() {
        if (!$this->input->is_ajax_request() && $this->input->method() !== 'post') {
            show_404();
            return;
        }

        $client_id = $this->security->xss_clean($this->input->post('client_id'));
        $session_id = $this->security->xss_clean($this->input->post('session_id'));
        $query = $this->security->xss_clean($this->input->post('query'));
        $response_text = $this->security->xss_clean($this->input->post('response_text'));
        $rating = $this->security->xss_clean($this->input->post('rating')); // thumbs_up or thumbs_down

        if (!in_array($rating, array('thumbs_up', 'thumbs_down'))) {
            $this->output
                ->set_content_type('application/json')
                ->set_status_header(400)
                ->set_output(json_encode(array('status' => 'error', 'message' => 'Invalid rating.')));
            return;
        }

        if (isset($this->feedback_model)) {
            try {
                $this->feedback_model->record_feedback($client_id, $session_id, $query, $response_text, $rating);
            } catch (Exception $e) {
                log_message('error', 'Feedback model recording failed: ' . $e->getMessage());
            }
        }

        $this->output
            ->set_content_type('application/json')
            ->set_output(json_encode(array(
                'status' => 'success',
                'message' => 'Feedback saved.',
                'csrf_hash' => $this->security->get_csrf_hash()
            )));
    }
}
