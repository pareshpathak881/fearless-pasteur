"""Document parsing and chunking engine with metadata extraction for Project Atlas.

Parses Markdown reports, detects page divisions (e.g. <!-- Page X -->),
extracts report-level and section-level metadata (sector, region, year, page),
and produces structured chunks.
"""

import os
import re
from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class DocumentChunk:
    chunk_id: str
    report_id: str
    report_title: str
    publisher: str
    sector: str
    region: str
    year: str
    page: int
    access_tier: str
    content: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReportChunker:
    def __init__(self, target_chunk_size: int = 350, overlap_size: int = 50):
        self.target_chunk_size = target_chunk_size
        self.overlap_size = overlap_size

    def parse_report_file(self, file_path: str) -> List[DocumentChunk]:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        # Extract frontmatter / header info
        report_id = ""
        report_title = ""
        publisher = ""
        sector = "Utilities"
        access_tier = "paid"

        m_id = re.search(r"\*\*Report ID:\*\*\s*([^\n\r]+)", raw_text)
        if m_id:
            report_id = m_id.group(1).strip()
        else:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            report_id = base_name

        m_title = re.search(r"^#\s+([^\n\r]+)", raw_text, re.MULTILINE)
        if m_title:
            report_title = m_title.group(1).strip()

        m_pub = re.search(r"\*\*Publisher:\*\*\s*([^\n\r]+)", raw_text)
        if m_pub:
            publisher = m_pub.group(1).strip()

        m_sec = re.search(r"\*\*Sector:\*\*\s*([^\n\r]+)", raw_text)
        if m_sec:
            sector = m_sec.group(1).strip()

        m_acc = re.search(r"\*\*Access Tier:\*\*\s*([^\n\r]+)", raw_text)
        if m_acc:
            access_tier = m_acc.group(1).strip().lower()

        # Split into pages by <!-- Page X -->
        page_splits = re.split(r"<!--\s*Page\s+(\d+)\s*-->", raw_text)
        
        chunks: List[DocumentChunk] = []
        chunk_counter = 1

        if len(page_splits) > 1:
            # page_splits: [preamble, page_num1, page_content1, page_num2, page_content2, ...]
            for i in range(1, len(page_splits), 2):
                page_num = int(page_splits[i])
                page_text = page_splits[i + 1].strip()
                page_chunks = self._chunk_page(
                    page_text, report_id, report_title, publisher, sector, access_tier, page_num, chunk_counter
                )
                chunk_counter += len(page_chunks)
                chunks.extend(page_chunks)
        else:
            # Fallback if no page comments: treat as page 1
            chunks = self._chunk_page(
                raw_text, report_id, report_title, publisher, sector, access_tier, 1, 1
            )

        return chunks

    def _chunk_page(
        self,
        text: str,
        report_id: str,
        report_title: str,
        publisher: str,
        sector: str,
        access_tier: str,
        page_num: int,
        start_counter: int
    ) -> List[DocumentChunk]:
        # Split by section headers or paragraphs
        sections = re.split(r"(?=^##?\s+)", text, flags=re.MULTILINE)
        result_chunks: List[DocumentChunk] = []
        cur_counter = start_counter

        for sec in sections:
            sec_clean = sec.strip()
            if not sec_clean:
                continue

            words = sec_clean.split()
            if len(words) <= self.target_chunk_size:
                c = self._create_chunk(
                    sec_clean, report_id, report_title, publisher, sector, access_tier, page_num, cur_counter
                )
                result_chunks.append(c)
                cur_counter += 1
            else:
                # Subdivide long sections
                step = self.target_chunk_size - self.overlap_size
                for start_idx in range(0, len(words), step):
                    chunk_words = words[start_idx : start_idx + self.target_chunk_size]
                    chunk_text = " ".join(chunk_words)
                    c = self._create_chunk(
                        chunk_text, report_id, report_title, publisher, sector, access_tier, page_num, cur_counter
                    )
                    result_chunks.append(c)
                    cur_counter += 1
                    if start_idx + self.target_chunk_size >= len(words):
                        break

        return result_chunks

    def _create_chunk(
        self,
        content: str,
        report_id: str,
        report_title: str,
        publisher: str,
        sector: str,
        access_tier: str,
        page_num: int,
        idx: int
    ) -> DocumentChunk:
        # Detect regional relevance
        region = "Global"
        upper = content.upper()
        if "ASIA-PACIFIC" in upper or "APAC" in upper:
            region = "APAC"
        elif "NORTH AMERICA" in upper or "US EPA" in upper:
            region = "North America"
        elif "EUROPE" in upper or "EU " in upper or "EMEA" in upper:
            region = "Europe"

        # Detect year relevance
        years = re.findall(r"\b(202[0-9]|203[0-5])\b", content)
        year_val = years[0] if years else "2024"

        chunk_id = f"{report_id}-P{page_num}-C{idx}"

        metadata = {
            "report_id": report_id,
            "report_title": report_title,
            "publisher": publisher,
            "sector": sector,
            "region": region,
            "year": year_val,
            "page": page_num,
            "access_tier": access_tier,
            "word_count": len(content.split())
        }

        return DocumentChunk(
            chunk_id=chunk_id,
            report_id=report_id,
            report_title=report_title,
            publisher=publisher,
            sector=sector,
            region=region,
            year=year_val,
            page=page_num,
            access_tier=access_tier,
            content=content,
            metadata=metadata
        )
