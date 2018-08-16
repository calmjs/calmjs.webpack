(function webpackUniversalModuleDefinition(root, factory) {
	if(typeof exports === 'object' && typeof module === 'object')
		module.exports = factory(require("global")["__calmjs__"]);
	else if(typeof define === 'function' && define.amd)
		define("__calmjs__", ["__calmjs__"], factory);
	else if(typeof exports === 'object')
		exports["__calmjs__"] = factory(require("global")["__calmjs__"]);
	else
		root["__calmjs__"] = factory(root["__calmjs__"]);
})(this, function(__WEBPACK_EXTERNAL_MODULE_1__) {
return /******/ (function(modules) { // webpackBootstrap
/******/ 	// The module cache
/******/ 	var installedModules = {};
/******/
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/
/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId]) {
/******/ 			return installedModules[moduleId].exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			i: moduleId,
/******/ 			l: false,
/******/ 			exports: {}
/******/ 		};
/******/
/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/
/******/ 		// Flag the module as loaded
/******/ 		module.l = true;
/******/
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/
/******/
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;
/******/
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;
/******/
/******/ 	// identity function for calling harmony imports with the correct context
/******/ 	__webpack_require__.i = function(value) { return value; };
/******/
/******/ 	// define getter function for harmony exports
/******/ 	__webpack_require__.d = function(exports, name, getter) {
/******/ 		if(!__webpack_require__.o(exports, name)) {
/******/ 			Object.defineProperty(exports, name, {
/******/ 				configurable: false,
/******/ 				enumerable: true,
/******/ 				get: getter
/******/ 			});
/******/ 		}
/******/ 	};
/******/
/******/ 	// getDefaultExport function for compatibility with non-harmony modules
/******/ 	__webpack_require__.n = function(module) {
/******/ 		var getter = module && module.__esModule ?
/******/ 			function getDefault() { return module['default']; } :
/******/ 			function getModuleExports() { return module; };
/******/ 		__webpack_require__.d(getter, 'a', getter);
/******/ 		return getter;
/******/ 	};
/******/
/******/ 	// Object.prototype.hasOwnProperty.call
/******/ 	__webpack_require__.o = function(object, property) { return Object.prototype.hasOwnProperty.call(object, property); };
/******/
/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "";
/******/
/******/ 	// Load entry module and return exports
/******/ 	return __webpack_require__(__webpack_require__.s = 5);
/******/ })
/************************************************************************/
/******/ ([
/* 0 */
/***/ (function(module, exports, __webpack_require__) {

"use strict";


var calmjs_bootstrap = __webpack_require__(1) || {};
var externals = calmjs_bootstrap.modules || {};
exports.modules = {
    "example/package/bad": __webpack_require__(2),
    "example/package/bare": __webpack_require__(6),
    "example/package/dynamic": __webpack_require__(7),
    "example/package/main": __webpack_require__(8),
    "example/package/math": __webpack_require__(3),
    "mockquery": __webpack_require__(4)
};

exports.require = function(modules, f) {
    if (modules.map) {
        f.apply(null, modules.map(function(m) {
            return exports.modules[m] || externals[m];
        }));
    }
    else {
        // assuming the synchronous version
        return exports.modules[modules] || externals[modules];
    }
};


/***/ }),
/* 1 */
/***/ (function(module, exports) {

module.exports = __WEBPACK_EXTERNAL_MODULE_1__;

/***/ }),
/* 2 */
/***/ (function(module, exports, __webpack_require__) {

"use strict";

var die = function() {
    return notdefinedsymbol;
};
exports.die = die;


/***/ }),
/* 3 */
/***/ (function(module, exports, __webpack_require__) {

"use strict";

exports.add = function(x, y) {
    return x + y;
};
exports.mul = function(x, y) {
    return x * y;
};


/***/ }),
/* 4 */
/***/ (function(module, exports, __webpack_require__) {

"use strict";


exports.mq = function(arg) {
    return [arg];
};


/***/ }),
/* 5 */
/***/ (function(module, exports, __webpack_require__) {

"use strict";


var calmjs_loader = __webpack_require__(0)
var calmjs_bootstrap = __webpack_require__(1) || {};
var external_modules = calmjs_bootstrap.modules || {};

exports.require = calmjs_loader.require;
exports.modules = external_modules;
for (var k in calmjs_loader.modules) {
    exports.modules[k] = calmjs_loader.modules[k];
}


/***/ }),
/* 6 */
/***/ (function(module, exports, __webpack_require__) {

"use strict";

var $ = __webpack_require__(4).mq;
exports.clean = function(arg) {
    return $(arg);
};


/***/ }),
/* 7 */
/***/ (function(module, exports, __webpack_require__) {

"use strict";

exports.check = function(arg, arg2) {
    var mockquery_name = "mockquery";
    var math_name = "example/package/math";
    var mq = __webpack_require__(0).require(mockquery_name).mq;
    var math = __webpack_require__(0).require(math_name);
    return math.add(mq(arg)[0], mq(arg2)[0]);
};


/***/ }),
/* 8 */
/***/ (function(module, exports, __webpack_require__) {

"use strict";

var math = __webpack_require__(3);
var bad = __webpack_require__(2);
var main = function(trigger) {
    console.log(math.add(1, 1));
    console.log(math.mul(2, 2));
    if (trigger === true) {
        bad.die();
    }
};
exports.main = main;


/***/ })
/******/ ]);
});