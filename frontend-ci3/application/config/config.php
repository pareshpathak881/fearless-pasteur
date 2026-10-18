<?php
defined('BASEPATH') OR exit('No direct script access allowed');

$config['base_url'] = getenv('CI_BASE_URL') ?: 'http://localhost:8080/';
$config['index_page'] = '';
$config['uri_protocol'] = 'REQUEST_URI';
$config['language'] = 'english';
$config['charset'] = 'UTF-8';
$config['enable_hooks'] = FALSE;
$config['subclass_prefix'] = 'MY_';
$config['composer_autoload'] = FALSE;
$config['permitted_uri_chars'] = 'a-z 0-9~%.:_\-';

// Security settings
$config['csrf_protection'] = TRUE;
$config['csrf_token_name'] = 'atlas_csrf_token';
$config['csrf_cookie_name'] = 'atlas_csrf_cookie';
$config['csrf_expire'] = 7200;
$config['csrf_regenerate'] = FALSE;
$config['csrf_exclude_uris'] = array();

$config['global_xss_filtering'] = TRUE;

// Python FastAPI Backend Endpoint
$config['copilot_api_url'] = getenv('COPILOT_API_URL') ?: 'http://copilot-api:8000';
$config['copilot_api_key'] = getenv('COPILOT_API_KEY') ?: 'atlas_secret_api_key_2025';
$config['copilot_timeout'] = 30; // 30 seconds request timeout
