<?php

namespace App\Services\Download;

readonly class DownloadResult
{
    public function __construct(
        public string $filePath,
        public int $fileSizeBytes,
        /** @var array<string, mixed> */
        public array $metadata,
    ) {}
}
