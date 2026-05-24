"""
中医智能诊断平台 - 后端API
支持真实AI识别的面诊和舌诊功能
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import sys
import os
import json
import numpy as np

def convert_numpy(obj):
    """递归将numpy类型转为Python原生类型，解决JSON序列化问题"""
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from face_diagnosis import FaceDiagnosis
from tongue_diagnosis import TongueDiagnosis
from voice_diagnosis import VoiceDiagnosis

# 创建FastAPI应用
app = FastAPI(
    title="中医智能诊断平台API",
    description="支持真实AI识别的面诊、舌诊、闻诊功能",
    version="1.1.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化诊断器
face_diagnosis = FaceDiagnosis()
tongue_diagnosis = TongueDiagnosis()
voice_diagnosis = VoiceDiagnosis()

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "中医智能诊断平台API",
        "version": "1.1.0",
        "endpoints": {
            "face_analysis": "/api/face/analyze",
            "tongue_analysis": "/api/tongue/analyze",
            "voice_analysis": "/api/voice/analyze",
            "health": "/health"
        }
    }

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}

@app.post("/api/face/analyze")
async def analyze_face(file: UploadFile = File(...)):
    """面诊分析接口"""
    # 读取图片数据
    contents = await file.read()
    print(f"[面诊] 收到文件: name={file.filename}, content_type={file.content_type}, size={len(contents)} bytes, header={contents[:16].hex() if contents else 'empty'}")
    
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="上传的文件为空")
    
    try:
        result = face_diagnosis.analyze(contents)
        return JSONResponse(content=convert_numpy(result))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.post("/api/tongue/analyze")
async def analyze_tongue(file: UploadFile = File(...)):
    """舌诊分析接口"""
    contents = await file.read()
    print(f"[舌诊] 收到文件: name={file.filename}, content_type={file.content_type}, size={len(contents)} bytes, header={contents[:16].hex() if contents else 'empty'}")
    
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="上传的文件为空")
    
    try:
        result = tongue_diagnosis.analyze(contents)
        return JSONResponse(content=convert_numpy(result))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

@app.post("/api/voice/analyze")
async def analyze_voice(file: UploadFile = File(...)):
    """闻诊（语声 + 语言节奏）分析接口"""
    contents = await file.read()
    print(f"[闻诊] 收到文件: name={file.filename}, content_type={file.content_type}, size={len(contents)} bytes, header={contents[:16].hex() if contents else 'empty'}")

    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="上传的录音为空")

    try:
        result = voice_diagnosis.analyze(contents, original_filename=file.filename or "audio")
        return JSONResponse(content=convert_numpy(result))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {str(e)}")

if __name__ == "__main__":
    print("🚀 中医智能诊断平台API启动中...")
    print("📍 访问地址: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
