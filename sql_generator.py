import os
from transformers import AutoModelForCausalLM, AutoModelForSeq2SeqLM, AutoTokenizer
import torch


class SQLGenerator:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        model_path = "model"
        if os.path.exists(os.path.join(model_path, "config.json")):
            try:
                print(f"Loading model from: {model_path}")
                import json
                with open(os.path.join(model_path, "config.json")) as f:
                    config = json.load(f)
                
                # Check model type
                model_type = config.get("model_type", "")
                is_encoder_decoder = config.get("is_encoder_decoder", False)
                
                # Load tokenizer
                try:
                    self.tokenizer = AutoTokenizer.from_pretrained(
                        model_path, trust_remote_code=True, local_files_only=True
                    )
                except Exception:
                    # Try to load from HuggingFace if local fails
                    model_name = config.get("_name_or_path", "")
                    if model_name:
                        print(f"Loading tokenizer from HuggingFace: {model_name}")
                        self.tokenizer = AutoTokenizer.from_pretrained(
                            model_name, trust_remote_code=True
                        )
                    else:
                        # Fallback to T5 tokenizer
                        self.tokenizer = AutoTokenizer.from_pretrained(
                            "t5-small", trust_remote_code=True
                        )
                
                if self.tokenizer.pad_token is None:
                    self.tokenizer.pad_token = self.tokenizer.eos_token
                
                # Load model based on type
                if is_encoder_decoder or model_type == "t5":
                    print("Loading T5 (encoder-decoder) model...")
                    self.model = AutoModelForSeq2SeqLM.from_pretrained(
                        model_path,
                        torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                        device_map="auto" if self.device == "cuda" else None,
                        trust_remote_code=True,
                        local_files_only=True
                    )
                else:
                    print("Loading causal LM model...")
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_path,
                        torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                        device_map="auto" if self.device == "cuda" else None,
                        trust_remote_code=True,
                        local_files_only=True
                    )
                print("Model loaded successfully!")
                return
            except Exception as e:
                print(f"Failed to load model: {e}")
                import traceback
                traceback.print_exc()
        print("Model not found. Using fallback.")

    def _get_schema(self):
        return """CREATE TABLE videos (
    id VARCHAR(255) PRIMARY KEY,
    creator_id VARCHAR(255) NOT NULL,
    video_created_at TIMESTAMP NOT NULL,
    views_count INTEGER NOT NULL DEFAULT 0,
    likes_count INTEGER NOT NULL DEFAULT 0,
    comments_count INTEGER NOT NULL DEFAULT 0,
    reports_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE video_snapshots (
    id BIGSERIAL PRIMARY KEY,
    video_id VARCHAR(255) NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    views_count INTEGER NOT NULL DEFAULT 0,
    likes_count INTEGER NOT NULL DEFAULT 0,
    comments_count INTEGER NOT NULL DEFAULT 0,
    reports_count INTEGER NOT NULL DEFAULT 0,
    delta_views_count INTEGER NOT NULL DEFAULT 0,
    delta_likes_count INTEGER NOT NULL DEFAULT 0,
    delta_comments_count INTEGER NOT NULL DEFAULT 0,
    delta_reports_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);"""

    def generate_sql(self, query):
        if not self.model or not self.tokenizer:
            return "SELECT COUNT(*) FROM videos"

        # T5 prompt format
        schema = self._get_schema()
        prompt = f"""translate to SQL: {query}

{schema}"""

        try:
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512).to(self.device)
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs.input_ids,
                    max_new_tokens=128,
                    temperature=0.3,
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id or 0,
                    eos_token_id=self.tokenizer.eos_token_id or 1,
                    repetition_penalty=1.2,
                    num_beams=2
                )
                # For T5, decode only the generated part
                sql = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
                
                # Clean SQL
                for prefix in ["```sql", "```", "SQL query:", "SQL:"]:
                    if prefix in sql:
                        sql = sql.split(prefix)[-1].strip()
                
                if sql.endswith("```"):
                    sql = sql[:-3].strip()
                
                # Extract SQL if present
                if "SELECT" in sql:
                    sql = sql[sql.find("SELECT"):]
                    if ";" in sql:
                        sql = sql[:sql.index(";")].strip()
                    elif "\n" in sql:
                        sql = sql[:sql.index("\n")].strip()
                
                # Fix wrong table/column names from T5
                import re
                # Remove TABLE_ prefix and fix underscores
                sql = re.sub(r'(?i)TABLE_video_snapshots[_]*', 'video_snapshots', sql)
                sql = re.sub(r'(?i)TABLE_videos[_]*', 'videos', sql)
                sql = re.sub(r'table_video_snapshots[_]*', 'video_snapshots', sql, flags=re.IGNORECASE)
                sql = re.sub(r'table_videos[_]*', 'videos', sql, flags=re.IGNORECASE)
                # Remove long underscore sequences
                sql = re.sub(r'video_snapshots[_]{3,}', 'video_snapshots', sql)
                sql = re.sub(r'videos[_]{3,}', 'videos', sql)
                # Remove any remaining long underscore sequences anywhere
                sql = re.sub(r'[_]{10,}', '', sql)
                
                # If SQL is empty or invalid, use fallback
                if not sql or not sql.upper().startswith("SELECT"):
                    return self._fallback_sql(query)
                
                # Check if SQL is too short (just "SELECT table_name")
                sql_upper = sql.upper().strip()
                if sql_upper in ["SELECT VIDEO_SNAPSHOTS", "SELECT VIDEOS", 
                                 "SELECT VIDEO_SNAPSHOTS", "SELECT VIDEOS"]:
                    return self._fallback_sql(query)
                
                # Validate table names exist and SQL is complete
                if ("video_snapshots" in sql.lower() or "videos" in sql.lower()) and len(sql) > 20:
                    return sql
                else:
                    return self._fallback_sql(query)
        except Exception as e:
            print(f"LLM error: {e}")
            return self._fallback_sql(query)
    
    def _fallback_sql(self, query):
        """Simple fallback SQL generation"""
        import re
        q = query.lower()
        
        if "сколько всего видео" in q:
            return "SELECT COUNT(*) FROM videos"
        
        if "лайков" in q and "видео" in q:
            match = re.search(r'([a-f0-9-]{36})', query)
            if match:
                return f"SELECT likes_count FROM videos WHERE id = '{match.group(1)}'"
        
        if ("выросли" in q or "прирост" in q) and "просмотров" in q:
            match = re.search(r'(\d+)\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})', q)
            if match:
                months = {'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
                         'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
                         'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'}
                day, month, year = match.group(1), match.group(2), match.group(3)
                date = f"{year}-{months[month]}-{day.zfill(2)}"
                return f"SELECT COALESCE(SUM(delta_views_count), 0) FROM video_snapshots WHERE DATE(created_at) = '{date}'"
        
        if "креатора" in q:
            match = re.search(r'креатора\s+с\s+id\s+(\S+)', q)
            if match:
                return f"SELECT COUNT(*) FROM videos WHERE creator_id = '{match.group(1)}'"
        
        if "больше" in q and "просмотров" in q:
            match = re.search(r'больше\s+(\d+[\s,]*\d*)', q)
            if match:
                views = match.group(1).replace(' ', '').replace(',', '')
                return f"SELECT COUNT(*) FROM videos WHERE views_count > {views}"
        
        if "разных видео" in q and "просмотры" in q:
            match = re.search(r'(\d+)\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})', q)
            if match:
                months = {'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
                         'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
                         'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'}
                day, month, year = match.group(1), match.group(2), match.group(3)
                date = f"{year}-{months[month]}-{day.zfill(2)}"
                return f"SELECT COUNT(DISTINCT video_id) FROM video_snapshots WHERE DATE(created_at) = '{date}' AND delta_views_count > 0"
        
        return "SELECT COUNT(*) FROM videos"
