```python
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
import uuid
import json
from datetime import datetime, timedelta
import chardet

app = FastAPI(title="CSV Processor API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

data_storage = {}

def clean_data_storage():
    current_time = datetime.now()
    expired_keys = [
        key for key, value in data_storage.items()
        if current_time - value['timestamp'] > timedelta(hours=24)
    ]
    for key in expired_keys:
        del data_storage[key]

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    return result['encoding'] or 'utf-8'

def process_csv_content(file_content, file_type):
    encoding = detect_encoding(file_content)
    
    try:
        csv_text = file_content.decode(encoding)
    except:
        csv_text = file_content.decode('utf-8', errors='ignore')
    
    csv_text = csv_text.replace('\r\n', '\n').replace('\r', '\n')
    
    try:
        df = pd.read_csv(io.StringIO(csv_text), sep='\t')
        if len(df.columns) == 1:
            df = pd.read_csv(io.StringIO(csv_text), sep=',')
    except:
        df = pd.read_csv(io.StringIO(csv_text), sep=',')
    
    df = df.dropna(how='all')
    df = df.fillna('')
    
    processed_data = []
    
    if file_type == 'twitter':
        for _, row in df.iterrows():
            url = str(row.get('URL', row.get('Link', row.get('Post URL', ''))))
            headline = str(row.get('Headline', row.get('Title', row.get('Post Text', row.get('Content', '')))))
            author = str(row.get('Author', row.get('Screen Name', row.get('Username', 'Unknown'))))
            date = str(row.get('Date', row.get('Published', row.get('Created', ''))))
            
            if not headline.strip() and not url.strip():
                continue
                
            processed_data.append({
                'url': url,
                'headline': headline,
                'author': author,
                'date': date,
                'source': 'Twitter/X'
            })
    
    elif file_type == 'news':
        for _, row in df.iterrows():
            url = str(row.get('URL', row.get('Link', row.get('Article URL', ''))))
            headline = str(row.get('Headline', row.get('Title', row.get('Article Title', ''))))
            author = str(row.get('Author', row.get('Publication', row.get('Source', 'Unknown'))))
            date = str(row.get('Date', row.get('Published', row.get('Publication Date', ''))))
            
            if not headline.strip() and not url.strip():
                continue
                
            processed_data.append({
                'url': url,
                'headline': headline,
                'author': author,
                'date': date,
                'source': 'News'
            })
    
    return processed_data

@app.get("/")
async def root():
    return {"message": "CSV Processor API is running"}

@app.post("/upload-twitter")
async def upload_twitter_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        content = await file.read()
        processed_data = process_csv_content(content, 'twitter')
        data_id = str(uuid.uuid4())
        
        data_storage[data_id] = {
            'data': processed_data,
            'timestamp': datetime.now(),
            'type': 'twitter',
            'filename': file.filename
        }
        
        clean_data_storage()
        
        return {
            "message": "Twitter CSV processed successfully",
            "data_id": data_id,
            "data_url": f"/get-data/{data_id}",
            "records_processed": len(processed_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/upload-news")
async def upload_news_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        content = await file.read()
        processed_data = process_csv_content(content, 'news')
        data_id = str(uuid.uuid4())
        
        data_storage[data_id] = {
            'data': processed_data,
            'timestamp': datetime.now(),
            'type': 'news',
            'filename': file.filename
        }
        
        clean_data_storage()
        
        return {
            "message": "News CSV processed successfully",
            "data_id": data_id,
            "data_url": f"/get-data/{data_id}",
            "records_processed": len(processed_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/get-data/{data_id}")
async def get_processed_data(data_id: str):
    if data_id not in data_storage:
        raise HTTPException(status_code=404, detail="Data not found or expired")
    
    clean_data_storage()
    return data_storage[data_id]['data']
```
