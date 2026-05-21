<?php

namespace App\Services\Download;

use RuntimeException;

class YtDlpBinaryResolver
{
    /** @var list<string>|null */
    private static ?array $cachedPrefix = null;

    /**
     * Command prefix to invoke yt-dlp (executable path or `python -m yt_dlp`).
     *
     * @return list<string>
     */
    public function resolve(): array
    {
        if (self::$cachedPrefix !== null) {
            return self::$cachedPrefix;
        }

        $configured = (string) config('video_storage.ytdlp.path', 'yt-dlp');
        if ($configured !== '' && $configured !== 'yt-dlp') {
            self::$cachedPrefix = $this->prefixForPath($configured);

            return self::$cachedPrefix;
        }

        foreach ($this->candidateExecutables() as $executable) {
            if ($this->isRunnable($executable)) {
                self::$cachedPrefix = [$executable];

                return self::$cachedPrefix;
            }
        }

        $pythonModule = $this->pythonModulePrefix();
        if ($pythonModule !== null && $this->isRunnableProcess($pythonModule)) {
            self::$cachedPrefix = $pythonModule;

            return self::$cachedPrefix;
        }

        throw new RuntimeException(
            'yt-dlp is not installed or not on PATH. '
            .'Install: pip install yt-dlp  (Windows: add %APPDATA%\\Python\\Python311\\Scripts to PATH) '
            .'or set YTDLP_PATH in laravel/.env to the full path of yt-dlp.exe'
        );
    }

    /**
     * @return list<string>
     */
    private function prefixForPath(string $path): array
    {
        if (str_contains($path, ' ') && ! str_starts_with($path, '"')) {
            // Process accepts separate argv; path with spaces is fine as single element
        }

        if (is_file($path) || $this->isRunnable($path)) {
            return [$path];
        }

        throw new RuntimeException('YTDLP_PATH is not a runnable yt-dlp binary: '.$path);
    }

    /**
     * @return list<string>
     */
    private function candidateExecutables(): array
    {
        $candidates = ['yt-dlp', 'yt-dlp.exe'];

        $appData = getenv('APPDATA');
        if (is_string($appData) && $appData !== '') {
            $candidates[] = $appData.'\\Python\\Python311\\Scripts\\yt-dlp.exe';
            $candidates[] = $appData.'\\Python\\Python310\\Scripts\\yt-dlp.exe';
        }

        $localAppData = getenv('LOCALAPPDATA');
        if (is_string($localAppData) && $localAppData !== '') {
            $candidates[] = $localAppData.'\\Programs\\Python\\Python311\\Scripts\\yt-dlp.exe';
        }

        $candidates[] = 'C:\\Program Files\\Python311\\Scripts\\yt-dlp.exe';

        return array_values(array_unique($candidates));
    }

    /**
     * @return list<string>|null
     */
    private function pythonModulePrefix(): ?array
    {
        foreach (['python', 'python3', 'C:\\Program Files\\Python311\\python.exe'] as $python) {
            if ($this->isRunnableProcess([$python, '-m', 'yt_dlp', '--version'])) {
                return [$python, '-m', 'yt_dlp'];
            }
        }

        return null;
    }

    private function isRunnable(string $command): bool
    {
        return $this->isRunnableProcess([$command, '--version']);
    }

    /**
     * @param  list<string>  $command
     */
    private function isRunnableProcess(array $command): bool
    {
        $binary = $command[0];
        if ($binary !== 'yt-dlp' && $binary !== 'yt-dlp.exe' && ! is_file($binary) && ! $this->commandExistsOnPath($binary)) {
            if (! str_ends_with(strtolower($binary), 'python.exe') && $binary !== 'python' && $binary !== 'python3') {
                return false;
            }
        }

        $process = new \Symfony\Component\Process\Process($command, null, null, null, 15.0);
        try {
            $process->run();

            return $process->isSuccessful();
        } catch (\Throwable) {
            return false;
        }
    }

    private function commandExistsOnPath(string $command): bool
    {
        if (is_file($command)) {
            return true;
        }

        $where = new \Symfony\Component\Process\Process(['where', $command], null, null, null, 10.0);
        $where->run();

        return $where->isSuccessful() && trim($where->getOutput()) !== '';
    }
}
