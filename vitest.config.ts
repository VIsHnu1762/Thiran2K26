/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
    plugins: [react()],
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: ['./tests/setup.ts'],
        include: ['tests/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
        exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html', 'lcov'],
            reportsDirectory: './coverage',
            include: ['components/**/*.{ts,tsx}', 'services/**/*.{ts,tsx}'],
            exclude: [
                'node_modules/**',
                'tests/**',
                '**/*.d.ts',
                '**/*.test.{ts,tsx}',
                '**/*.spec.{ts,tsx}',
            ],
            thresholds: {
                statements: 50,
                branches: 50,
                functions: 50,
                lines: 50,
            },
        },
        reporters: ['verbose', 'html'],
        testTimeout: 10000,
        hookTimeout: 10000,
    },
    resolve: {
        alias: {
            '@': resolve(__dirname, './'),
            '@components': resolve(__dirname, './components'),
            '@services': resolve(__dirname, './services'),
        },
    },
});
