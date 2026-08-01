# 도구

로지아의 네 장을 빚고 잠그고 올리는 도구들. 비밀은 하나도 들어 있지 않다.
암호와 토큰은 드롭박스 `01. Projects/00. Job Search/board_keys.txt` 에만 있다.

```
build.py     loggia-data.json → site/ 네 장
lock.js      한 장을 AES-256 으로 잠근다
publish.sh   네 장을 한 소금으로 잠가 한 번에 올린다
```

## 쓰는 순서

```bash
git clone https://github.com/eeruwang/loggia.git
python loggia/tools/build.py loggia-data.json site/
bash   loggia/tools/publish.sh site/ "<암호>" "<토큰>" "<커밋 말>"
```

`loggia-data.json` 은 드롭박스의 같은 폴더에 있다. 여기에는 두지 않는다.
이 저장소는 공개라서 내용이 드러나기 때문이다. 올라가는 판은 전부 암호문이다.
