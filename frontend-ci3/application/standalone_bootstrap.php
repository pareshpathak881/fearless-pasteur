<?php
/**
 * Standalone CodeIgniter 3 Runtime Kernel & Dispatcher
 * Project Atlas - Cognitive Market Research
 * 
 * Provides standard CI3 core abstractions (CI_Controller, CI_Model, Loader,
 * Security, Input, Output) ensuring 100% portable execution under Apache or PHP CLI server.
 */

if (!defined('BASEPATH')) define('BASEPATH', dirname(__FILE__) . '/../system/');
if (!defined('APPPATH')) define('APPPATH', dirname(__FILE__) . '/');
if (!defined('VIEWPATH')) define('VIEWPATH', APPPATH . 'views/');

// Helper functions
function html_escape($var, $double_encode = TRUE) {
    if (empty($var)) return $var;
    if (is_array($var)) {
        foreach (array_keys($var) as $key) {
            $var[$key] = html_escape($var[$key], $double_encode);
        }
        return $var;
    }
    return htmlspecialchars($var, ENT_QUOTES, 'UTF-8', $double_encode);
}

function base_url($uri = '') {
    $base = getenv('CI_BASE_URL') ?: 'http://localhost:8080/';
    return rtrim($base, '/') . '/' . ltrim($uri, '/');
}

function log_message($level, $message) {
    // Basic logger
    error_log("[CI3-{$level}] {$message}");
}

function show_404() {
    header("HTTP/1.1 404 Not Found");
    echo "404 Page Not Found";
    exit;
}

// Security Class
class CI_Security {
    protected $csrf_hash;
    protected $csrf_token_name = 'atlas_csrf_token';

    public function __construct() {
        if (!isset($_SESSION)) {
            @session_start();
        }
        if (empty($_SESSION['atlas_csrf_hash'])) {
            $_SESSION['atlas_csrf_hash'] = bin2hex(random_bytes(16));
        }
        $this->csrf_hash = $_SESSION['atlas_csrf_hash'];
    }

    public function get_csrf_token_name() {
        return $this->csrf_token_name;
    }

    public function get_csrf_hash() {
        return $this->csrf_hash;
    }

    public function xss_clean($str) {
        if (is_array($str)) {
            foreach ($str as $k => $v) {
                $str[$k] = $this->xss_clean($v);
            }
            return $str;
        }
        return htmlspecialchars(strip_tags(trim($str)), ENT_QUOTES, 'UTF-8');
    }
}

// Input Class
class CI_Input {
    public function post($index = NULL, $xss_clean = FALSE) {
        if ($index === NULL) return $_POST;
        return isset($_POST[$index]) ? $_POST[$index] : NULL;
    }

    public function method($upper = FALSE) {
        $m = isset($_SERVER['REQUEST_METHOD']) ? $_SERVER['REQUEST_METHOD'] : 'GET';
        return $upper ? strtoupper($m) : strtolower($m);
    }

    public function is_ajax_request() {
        return (!empty($_SERVER['HTTP_X_REQUESTED_WITH']) && strtolower($_SERVER['HTTP_X_REQUESTED_WITH']) === 'xmlhttprequest');
    }
}

// Output Class
class CI_Output {
    protected $status_code = 200;
    protected $content_type = 'text/html';
    protected $body = '';

    public function set_status_header($code = 200) {
        $this->status_code = $code;
        http_response_code($code);
        return $this;
    }

    public function set_content_type($mime, $charset = 'UTF-8') {
        $this->content_type = $mime;
        header("Content-Type: {$mime}; charset={$charset}");
        return $this;
    }

    public function set_output($output) {
        $this->body = $output;
        echo $this->body;
        return $this;
    }
}

// Database Mock / Wrapper for CI3 Model
class CI_DB {
    public function insert($table, $data) {
        // Log to database or error log
        return true;
    }

    public function where($k, $v) { return $this; }
    public function update($table, $data) { return true; }
    public function order_by($k, $dir) { return $this; }
    public function get($table, $limit = 20) {
        return new class {
            public function result_array() { return array(); }
        };
    }
}

// Base Model
class CI_Model {
    public $db;
    public function __construct() {
        $this->db = new CI_DB();
    }
}

// Loader Class
class CI_Loader {
    protected $ci;

    public function __construct(&$ci) {
        $this->ci = &$ci;
    }

    public function library($lib, $params = NULL) {
        $className = ucfirst($lib);
        $file = APPPATH . 'libraries/' . $className . '.php';
        if (file_exists($file)) {
            require_once $file;
            $this->ci->$lib = new $className($params);
        }
    }

    public function helper($helpers) {
        // helpers loaded globally
    }

    public function model($model) {
        $className = ucfirst($model);
        $file = APPPATH . 'models/' . $className . '.php';
        if (file_exists($file)) {
            require_once $file;
            $this->ci->$model = new $className();
        }
    }

    public function database() {
        $this->ci->db = new CI_DB();
    }

    public function view($view, $vars = array(), $return = FALSE) {
        extract($vars);
        $viewFile = VIEWPATH . $view . '.php';
        if (file_exists($viewFile)) {
            if ($return) {
                ob_start();
                include $viewFile;
                return ob_get_clean();
            } else {
                include $viewFile;
            }
        } else {
            echo "View not found: " . html_escape($viewFile);
        }
    }
}

// Base Controller
class CI_Controller {
    private static $instance;
    public $load;
    public $security;
    public $input;
    public $output;

    public function __construct() {
        self::$instance = &$this;
        $this->security = new CI_Security();
        $this->input = new CI_Input();
        $this->output = new CI_Output();
        $this->load = new CI_Loader($this);
    }

    public static function &get_instance() {
        return self::$instance;
    }
}

// Router & Dispatcher Execution
$request_uri = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
$parts = array_values(array_filter(explode('/', trim($request_uri, '/'))));

$controllerName = !empty($parts[0]) ? ucfirst($parts[0]) : 'Chat';
$methodName = !empty($parts[1]) ? strtolower($parts[1]) : 'index';

// Normalize for chat controller
if (in_array(strtolower($controllerName), array('index.php', ''))) {
    $controllerName = 'Chat';
    $methodName = !empty($parts[1]) ? strtolower($parts[1]) : 'index';
}

$controllerFile = APPPATH . 'controllers/' . $controllerName . '.php';

if (file_exists($controllerFile)) {
    require_once $controllerFile;
    if (class_exists($controllerName)) {
        $controllerInstance = new $controllerName();
        if (method_exists($controllerInstance, $methodName)) {
            $controllerInstance->$methodName();
            exit;
        }
    }
}

// Default fallback to Chat::index()
require_once APPPATH . 'controllers/Chat.php';
$chatInstance = new Chat();
$chatInstance->index();
