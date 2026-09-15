import js from "@eslint/js";
import globals from "globals";

export default [
    {
        ignores: [
            "build*/**",
            "node_modules/**",
        ],
    },
    js.configs.recommended,
    {
        files: [
            "catchall/static/app.js",
            "catchall/static/audio-capture.js",
            "catchall/static/connection-lifecycle.js",
        ],
        languageOptions: {
            sourceType: "module",
            globals: {
                ...globals.browser,
            },
        },
    },
    {
        files: ["catchall/static/capture-worklet.js"],
        languageOptions: {
            sourceType: "module",
            globals: {
                AudioWorkletProcessor: "readonly",
                registerProcessor: "readonly",
                sampleRate: "readonly",
            },
        },
    },
    {
        files: ["tests/**/*.js"],
        languageOptions: {
            globals: {
                ...globals.node,
            },
        },
    },
];
