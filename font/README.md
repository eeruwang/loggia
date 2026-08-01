# 글꼴

`Pretendard-subset.woff2` 는 Pretendard Variable 을 잘라 둔 것이다.
한글 상용 2350자(KS X 1001)에 라틴과 유럽 글자와 기호, 그리고 판에 실제로
쓰인 글자를 더했다. 2,825자, 445KB. 원본은 2,009KB 다.

남의 자리에서 부르지 않고 이 저장소에서 부른다.
그래야 그 자리가 막히거나 느려도 판의 얼굴이 바뀌지 않는다.

## 다시 자르려면

새 글자가 판에 들어와 네모로 보이면 다시 자른다.

```bash
curl -sfLO https://raw.githubusercontent.com/orioncactus/pretendard/main/packages/pretendard/dist/web/variable/woff2/PretendardVariable.woff2
pip install fonttools brotli
python3 -m fontTools.subset PretendardVariable.woff2 \
  --text-file=글자목록.txt --flavor=woff2 --with-zopfli \
  --layout-features=kern,liga,calt,ccmp,locl,mark,mkmk \
  --output-file=font/Pretendard-subset.woff2
```

## 쓸 권리

SIL Open Font License 1.1. `LICENSE-Pretendard.txt` 를 볼 것.
Copyright 2021 Kil Hyung-jin. 자른 것을 다시 나눠도 되나 이 글을 함께 둔다.
