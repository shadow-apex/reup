<?php

namespace Tests\Unit;

use App\Services\Download\DouyinUrlNormalizer;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

class DouyinUrlNormalizerTest extends TestCase
{
    private DouyinUrlNormalizer $normalizer;

    protected function setUp(): void
    {
        parent::setUp();
        $this->normalizer = new DouyinUrlNormalizer;
    }

    #[DataProvider('douyinUrlProvider')]
    public function test_normalize_douyin_urls(string $input, string $expected): void
    {
        $this->assertSame($expected, $this->normalizer->normalize($input));
    }

    /**
     * @return array<string, array{0: string, 1: string}>
     */
    public static function douyinUrlProvider(): array
    {
        return [
            'jingxuan modal_id' => [
                'https://www.douyin.com/jingxuan?modal_id=7614898344946683171',
                'https://www.douyin.com/video/7614898344946683171',
            ],
            'canonical video' => [
                'https://www.douyin.com/video/7614898344946683171',
                'https://www.douyin.com/video/7614898344946683171',
            ],
            'share video path' => [
                'https://www.douyin.com/share/video/12345678901',
                'https://www.douyin.com/video/12345678901',
            ],
            'non douyin unchanged' => [
                'https://www.youtube.com/watch?v=abc',
                'https://www.youtube.com/watch?v=abc',
            ],
        ];
    }
}
