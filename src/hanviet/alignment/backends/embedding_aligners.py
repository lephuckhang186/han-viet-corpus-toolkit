"""Optional embedding-based aligners (Bertalign and Vecalign); kept disabled by default."""
from __future__ import annotations

from functools import lru_cache, partial
from pathlib import Path
import sys
from unittest.mock import patch

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
EMBEDDING_ONNX_FILE = "onnx/model_quint8_avx2.onnx"
EMBEDDING_FILES = (
    "config.json",
    "config_sentence_transformers.json",
    "modules.json",
    "sentence_bert_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "1_Pooling/config.json",
    EMBEDDING_ONNX_FILE,
)
MAX_ALIGNMENT_SIZE = 5


@lru_cache(maxsize=1)
def load_embedding_model(cache_dir):
    for name in ("bertalign", "vecalign"):
        checkout = cache_dir.parent / name
        if checkout.is_dir() and str(checkout) not in sys.path:
            sys.path.append(str(checkout))

    from huggingface_hub import snapshot_download
    from huggingface_hub.errors import LocalEntryNotFoundError
    from sentence_transformers import SentenceTransformer

    options = {"revision": EMBEDDING_REVISION, "cache_dir": cache_dir, "token": False}
    try:
        snapshot = Path(snapshot_download(EMBEDDING_MODEL, local_files_only=True, **options))
    except LocalEntryNotFoundError:
        snapshot = None
    if snapshot is None or not all((snapshot / file).is_file() for file in EMBEDDING_FILES):
        snapshot = Path(snapshot_download(EMBEDDING_MODEL, allow_patterns=EMBEDDING_FILES, **options))
    return SentenceTransformer(
        str(snapshot),
        device="cpu",
        backend="onnx",
        local_files_only=True,
        token=False,
        model_kwargs={"file_name": EMBEDDING_ONNX_FILE, "provider": "CPUExecutionProvider", "export": False},
    )


def links_from_indices(han, nghia, alignments):
    links = []
    for source, target in alignments:
        if any(not 0 <= i < len(han) for i in source) or any(not 0 <= i < len(nghia) for i in target):
            raise ValueError("Model trả về vị trí ngoài danh sách đơn vị đầu vào.")
        if len(source) and len(target):
            links.append({
                "han_ids": [han[i]["id"] for i in source],
                "nghia_ids": [nghia[i]["id"] for i in target],
            })
    return links


def align_bert(han, nghia, encoder):
    """Use the upstream two-pass aligner with presegmented text and local language labels."""
    with patch("sentence_transformers.SentenceTransformer", return_value=encoder):
        from bertalign import aligner

    src = "\n".join(item["text"] for item in han)
    dst = "\n".join(item["text"] for item in nghia)
    encode = partial(encoder.encode, normalize_embeddings=True, show_progress_bar=False)
    with (
        patch.object(aligner, "detect_lang", side_effect=["zh", "vi"]),
        patch.dict(aligner.LANG.ISO, {"zh": "Chinese", "vi": "Vietnamese"}),
        patch.object(encoder, "encode", encode),
        patch.object(aligner.model, "model", encoder),
        patch.object(aligner.model, "model_name", EMBEDDING_MODEL),
    ):
        model = aligner.Bertalign(
            src, dst, is_split=True, max_align=MAX_ALIGNMENT_SIZE, top_k=min(3, len(nghia))
        )
        model.align_sents()
    return links_from_indices(han, nghia, model.result)


def vecalign_embeddings(units, encoder, dp_utils):
    import numpy as np

    lines = [item["text"] for item in units]
    overlap_count = MAX_ALIGNMENT_SIZE - 1
    overlaps = list(dict.fromkeys(dp_utils.yield_overlaps(lines, overlap_count)))
    values = encoder.encode(overlaps, normalize_embeddings=True, show_progress_bar=False)
    embeddings = np.ascontiguousarray(values, dtype=np.float32)
    positions = {line: i for i, line in enumerate(overlaps)}
    return dp_utils.make_doc_embedding(positions, embeddings, lines, overlap_count)


def align_vecalign(han, nghia, encoder):
    """Run upstream VecAlign on the same embedding space as BERTAlign."""
    import numpy as np
    from vecalign import dp_utils

    source = vecalign_embeddings(han, encoder, dp_utils)
    target = vecalign_embeddings(nghia, encoder, dp_utils)
    previous_state = np.random.get_state()
    try:
        np.random.seed(42)
        stack = dp_utils.vecalign(
            vecs0=source,
            vecs1=target,
            final_alignment_types=dp_utils.make_alignment_types(MAX_ALIGNMENT_SIZE),
            del_percentile_frac=0.2,
            width_over2=8,
            max_size_full_dp=300,
            costs_sample_size=20_000,
            num_samps_for_norm=100,
        )
    finally:
        np.random.set_state(previous_state)
    return links_from_indices(han, nghia, stack[0]["final_alignments"])
