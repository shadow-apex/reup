<?php

namespace App\Services\Download;

readonly class ResolvedSourceUrl
{
    public function __construct(
        public string $originalUrl,
        public string $downloadUrl,
        public string $platform,
    ) {}

    public function wasNormalized(): bool
    {
        return $this->originalUrl !== $this->downloadUrl;
    }
}

class SourceUrlResolver
{
    public function __construct(
        private readonly PlatformResolver $platformResolver = new PlatformResolver,
        private readonly DouyinUrlNormalizer $douyinUrlNormalizer = new DouyinUrlNormalizer,
    ) {}

    public function resolve(string $url): ResolvedSourceUrl
    {
        $originalUrl = trim($url);
        $platform = $this->platformResolver->resolve($originalUrl);

        $downloadUrl = match ($platform) {
            'douyin' => $this->douyinUrlNormalizer->normalize($originalUrl),
            default => $originalUrl,
        };

        return new ResolvedSourceUrl($originalUrl, $downloadUrl, $platform);
    }
}
