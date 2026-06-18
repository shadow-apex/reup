<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\WebController;

// ─── Web UI ──────────────────────────────────────────────────────────

Route::prefix('web')->name('web.')->group(function () {
    Route::get('/', [WebController::class, 'dashboard'])->name('dashboard');

    // Download from URL
    Route::get('/download', [WebController::class, 'downloadForm'])->name('download');
    Route::post('/download', [WebController::class, 'downloadSubmit'])->name('download.submit');

    // Upload local file
    Route::get('/upload', [WebController::class, 'uploadForm'])->name('upload');
    Route::post('/upload', [WebController::class, 'uploadSubmit'])->name('upload.submit');

    // Process video
    Route::get('/process', [WebController::class, 'processForm'])->name('process');
    Route::post('/process', [WebController::class, 'processSubmit'])->name('process.submit');

    // History / job detail
    Route::get('/history', [WebController::class, 'history'])->name('history');
    Route::get('/jobs/{id}', [WebController::class, 'jobDetail'])->name('job-detail');

    // Settings
    Route::get('/settings', [WebController::class, 'settingsForm'])->name('settings');
    Route::post('/settings', [WebController::class, 'settingsSave'])->name('settings.save');

    // AI translate test
    Route::post('/translate-test', [WebController::class, 'translateTest'])->name('translate-test');
});
