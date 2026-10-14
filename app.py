import os
import random
import pandas as pd
import streamlit as st
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client["eshop_brasil"]

st.set_page_config(page_title="E-Shop Brasil", layout="wide")
st.title("E-Shop Brasil - Gestão de Dados")

menu = st.sidebar.selectbox("Menu", ["Inserir Dados", "Gerenciar", "Consultas", "Concatenação"])

NOMES = ["Ana", "Bruno", "Carla", "Diego", "Eva", "Flavio"]
CIDADES = ["São Paulo", "Manaus", "Fortaleza", "Recife", "Porto Alegre"]
CATEGORIAS = ["Eletrônicos", "Moda", "Casa", "Esporte"]

if menu == "Inserir Dados":
    st.header("Inserir cliente")
    nome = st.text_input("Nome")
    cidade = st.selectbox("Cidade", CIDADES)
    if st.button("Salvar cliente"):
        db.clientes.insert_one({"nome": nome, "cidade": cidade})
        st.success("Salvo!")

    if st.button("Gerar 50 clientes falsos"):
        for _ in range(50):
            db.clientes.insert_one({"nome": random.choice(NOMES), "cidade": random.choice(CIDADES)})
        st.success("50 clientes gerados!")

    if st.button("Gerar 20 pedidos falsos"):
        # Cada pedido guarda o _id de um cliente que já existe (chave de ligação)
        ids_clientes = [c["_id"] for c in db.clientes.find({}, {"_id": 1})]
        if not ids_clientes:
            st.warning("Gere ou cadastre clientes primeiro.")
        else:
            for _ in range(20):
                db.pedidos.insert_one({
                    "cliente_id": random.choice(ids_clientes),
                    "categoria": random.choice(CATEGORIAS),
                    "valor": round(random.uniform(50, 2000), 2),
                    "cidade": random.choice(CIDADES),
                })
            st.success("20 pedidos gerados!")

elif menu == "Gerenciar":
    st.header("Editar e Excluir")
    docs = list(db.clientes.find())
    if docs:
        df = pd.DataFrame(docs)
        st.dataframe(df)
        escolha = st.selectbox("Escolha o ID", [str(d["_id"]) for d in docs])
        novo_nome = st.text_input("Novo nome")
        if st.button("Editar"):
            id_doc = docs[[str(d["_id"]) for d in docs].index(escolha)]["_id"]
            db.clientes.update_one({"_id": id_doc}, {"$set": {"nome": novo_nome}})
            st.success("Editado!")
            st.rerun()
        if st.button("Excluir"):
            id_doc = docs[[str(d["_id"]) for d in docs].index(escolha)]["_id"]
            db.clientes.delete_one({"_id": id_doc})
            st.success("Excluído!")
            st.rerun()

elif menu == "Consultas":
    st.header("Dashboard")
    st.metric("Total Clientes", db.clientes.count_documents({}))
    st.metric("Total Pedidos", db.pedidos.count_documents({}))
    pedidos = list(db.pedidos.find())
    if pedidos:
        df_p = pd.DataFrame(pedidos)
        st.subheader("Vendas por categoria")
        st.bar_chart(df_p["categoria"].value_counts())
        st.subheader("Pedidos por cidade")
        st.bar_chart(df_p["cidade"].value_counts())
        st.dataframe(df_p.tail(10))

elif menu == "Concatenação":
    st.header("Concatenação de Dados")
    # $lookup liga pedidos.cliente_id a clientes._id (1 pedido -> 1 cliente)
    # $unwind transforma a lista info_cliente em um único objeto
    # $project escolhe e renomeia as colunas finais
    pipeline = [
        {"$lookup": {
            "from": "clientes",
            "localField": "cliente_id",
            "foreignField": "_id",
            "as": "info_cliente",
        }},
        {"$unwind": "$info_cliente"},
        {"$project": {
            "_id": 0,
            "pedido_id": {"$toString": "$_id"},
            "cliente": "$info_cliente.nome",
            "cidade_cliente": "$info_cliente.cidade",
            "categoria": 1,
            "valor": 1,
            "cidade_pedido": "$cidade",
        }},
    ]
    resultado = list(db.pedidos.aggregate(pipeline))
    if resultado:
        colunas = ["pedido_id", "cliente", "cidade_cliente", "categoria", "valor", "cidade_pedido"]
        df_join = pd.DataFrame(resultado)[colunas]
        st.dataframe(df_join)
        st.success(f"{len(df_join)} registros concatenados")
    else:
        st.warning("Gere clientes e depois pedidos na aba Inserir Dados")
        