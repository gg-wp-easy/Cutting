import pandas as pd
from threading import Lock
from datetime import datetime
import uvicorn
from fastapi import FastAPI, HTTPException
from optimizer import optimize
from fastapi.middleware.cors import CORSMiddleware
import service
import model
from fastapi.responses import JSONResponse

app = FastAPI()
data_file = 'data.json'
history_lock = Lock()

# Настройка CORS middleware
origins = [
    "http://localhost",
    "http://localhost:3000",
    "null",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def calculate(options, stocks):
    try:
        result = optimize(stocks, options.cut_length, options.cut_count,
                          options.blade_thickness, options.cutting_angle, options.original_thickness)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return result


@app.post("/linear-cut/", tags=["linear-cut"])
def linear_cut(options_cut: model.LinearCutOptions):
    result = calculate(options_cut, [options_cut.original_length])
    with history_lock:
        service.write_in_json({'id': datetime.now().isoformat(),
                               'data_input': options_cut.model_dump(), 'data_result': result['maps']}, data_file)
    return result


@app.post("/linear-cut-dynamic", tags=["linear-cut-dynamic"])
def linear_cut_dynamic(options_cut: model.LinearCutOptions):
    return calculate(options_cut, [options_cut.original_length])


@app.post("/linear-multi-cut", tags=["linear-multi-cut-dynamic"])
def linear_multi_cut(options_cut: model.LinearMultiCutOptions):
    result = calculate(options_cut, options_cut.originals_length)
    with history_lock:
        service.write_in_json({'id': datetime.now().isoformat(),
                               'data_input': options_cut.model_dump(), 'data_result': result['maps'],
                               'stock_lengths': result['stock_lengths']}, data_file)
    return result


@app.post("/bivariate-cut")
async def bivariate_cut(options_cut: model.SquareCutOptions):
    pieces = options_cut.pieces
    material_width = options_cut.material_width
    material_height = options_cut.material_height
    result_maps = service.greedy_cutting_stock(pieces, material_width, material_height)
    return JSONResponse(content={"result_maps":result_maps})

@app.get("/history-cut", tags=["history-cut"])
async def history_cut(start_date: str):
    df = pd.read_json(data_file)
    df['id'] = pd.to_datetime(df['id'])
    desired_datas_data = df[df['id'] >= start_date]

    return desired_datas_data

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
