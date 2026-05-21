<?php

namespace App\Services\Download;

use App\Models\SourceVideo;
use Illuminate\Support\Facades\File;

class SourceVideoStorage
{
    public function basePath(): string
    {
        return (string) config('video_storage.base_path');
    }

    public function directoryFor(SourceVideo $sourceVideo): string
    {
        $created = $sourceVideo->created_at ?? now();
        $relative = implode(DIRECTORY_SEPARATOR, [
            (string) config('video_storage.sources_dir'),
            $created->format('Y'),
            $created->format('m'),
            (string) $sourceVideo->id,
        ]);

        $absolute = $this->basePath().DIRECTORY_SEPARATOR.$relative;
        File::ensureDirectoryExists($absolute);

        return $absolute;
    }

    public function destinationPath(SourceVideo $sourceVideo, string $extension): string
    {
        $ext = ltrim($extension, '.') ?: 'mp4';

        return $this->directoryFor($sourceVideo).DIRECTORY_SEPARATOR.'original.'.$ext;
    }

    public function outDir(): string
    {
        $path = $this->basePath().DIRECTORY_SEPARATOR.(string) config('video_storage.out_dir');
        File::ensureDirectoryExists($path);

        return $path;
    }
}
