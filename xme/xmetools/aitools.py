# from zhipuai import ZhipuAI

# def create_knowledge(client: ZhipuAI, name, desc, file_path):
#     result = client.knowledge.create(
#         embedding_id=3,
#         name=name,
#         description=desc
#     )
#     resp = client.knowledge.document.create(
#         file=open(file_path, "rb"),
#         purpose="retrieval",
#         knowledge_id="1798330146986561536"
#     )