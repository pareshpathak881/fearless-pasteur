<?php
defined('BASEPATH') OR exit('No direct script access allowed');

class Feedback_model extends CI_Model {

    public function __construct() {
        parent::__construct();
        $this->load->database();
    }

    /**
     * Record a chat interaction and optional thumbs feedback.
     */
    public function record_feedback($client_id, $session_id, $query, $response_text, $rating = null) {
        $data = array(
            'client_id'     => $client_id,
            'session_id'    => $session_id,
            'query'         => $query,
            'response_text' => $response_text,
            'rating'        => $rating
        );
        return $this->db->insert('chat_feedback', $data);
    }

    /**
     * Update rating for a specific session/query.
     */
    public function update_rating($id, $rating) {
        $this->db->where('id', $id);
        return $this->db->update('chat_feedback', array('rating' => $rating));
    }

    /**
     * Fetch recent feedback history.
     */
    public function get_recent_feedback($limit = 20) {
        $this->db->order_by('created_at', 'DESC');
        $query = $this->db->get('chat_feedback', $limit);
        return $query->result_array();
    }
}
