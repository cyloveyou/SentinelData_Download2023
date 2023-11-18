# _*_coding:utf-8_*_
# created by cy on 2023/11/12
# 公众号:小y只会写bug
# CSDN主页:https://blog.csdn.net/weixin_64989228?spm=1000.2115.3001.5343

import multiprocessing
import os
import re

import requests
from tqdm import tqdm

proxies = {
	"http": "替换位置一:替换位置二",
	"https": "替换位置一:替换位置二"
}  # todo 设置代理


class SentinelDownload:
	@staticmethod
	def CreatURL(urlStr: str) -> str:
		return urlStr.strip()

	@staticmethod
	def GetAccessToken(username: str, password: str) -> str:
		"""
		获取token,用于下载数据
		:param username: 用户名
		:param password: 密码
		:return:
		"""
		data = {
			"client_id": "cdse-public",
			"username": username,
			"password": password,
			"grant_type": "password",
		}
		try:
			r = requests.post("https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
							  data=data, proxies=proxies)
			r.raise_for_status()
		except Exception as e:
			raise Exception(f"Access token creation failed. Reponse from the server was: {r.json()}")
		print("token获取成功！")
		return r.json()["access_token"]

	@staticmethod
	def Search(SearchURL: str) -> list:
		"""
		检索数据
		:param SearchURL:构造的检索URL
		:return:
		"""
		resDf = []
		jsonInfo = requests.get(SearchURL, proxies=proxies).json()
		n = jsonInfo["@odata.count"]
		if n == 0:
			print("没有检索到数据")
		else:
			print(f"共检索到{n}条数据")
			for k in range(0, n, 900):
				print(f"正在进行第{k}次数据信息的检索")
				top = re.findall("(top=\d+)", SearchURL)[0]
				skip = re.findall("(skip=\d+)", SearchURL)[0]
				url = SearchURL.replace(top, f"top={900}").replace(skip, f"skip={k}")  # 修正url
				jsonInfo = requests.get(url, proxies=proxies).json()
				resDf += [{"Id": i["Id"], "Name": i["Name"]} for i in jsonInfo['value']]
		return resDf

	@staticmethod
	def Download1(DownloadInfo: list):
		"""
		单个数据文件的下载
		:param DownloadInfo:(tokenStr, productID, savePath)
		:return:
		"""
		tokenStr, productID, savePath = DownloadInfo
		url = f"http://zipper.dataspace.copernicus.eu/odata/v1/Products({productID})/$value"
		headers = {"Authorization": f"Bearer {tokenStr}"}  # 设置token
		response = requests.get(url, headers=headers, stream=True, proxies=proxies, timeout=10)
		if response.status_code == 200:
			data_size = round(float(response.headers['Content-Length'])) / 1024 / 1024
			print()
			with open(f'{savePath}.zip', 'wb') as f:
				for data in tqdm(iterable=response.iter_content(1024 * 1024), total=int(data_size), desc=f'{savePath}',
								 unit='MB'):
					f.write(data)
		else:
			print(response.text)
			raise Exception(f"Download failed. Response from the server was: {response.text}")

	@staticmethod
	def DownloadMain(DownloadInfoS: list, token, saveFolder):
		"""
		单线程下载数据
		:param DownloadInfoS:
		:param token:
		:param saveFolder:
		:return:
		"""
		# 循环下载
		for i in range(len(DownloadInfoS)):
			ID = DownloadInfoS[i]['Id']
			Name = DownloadInfoS[i]['Name']
			savePath = f"{saveFolder}/{Name}"
			InfoLi = [token, ID, savePath]
			try:
				SentinelDownload.Download1(InfoLi)
			except:
				print(f"{Name}下载失败,尝试更新token")
				SentinelDownload.Download1(InfoLi)
				continue

	@staticmethod
	def MultiDownload(DownloadInfoS: list, tokenStr: str, Folder: str):
		"""
		多线程下载数据
		:param DownloadInfoS:
		:param tokenStr:
		:param Folder:
		:return:
		"""
		Li = []
		for i in range(len(DownloadInfoS)):
			ID = DownloadInfoS[i]['Id']
			Name = DownloadInfoS[i]['Name']
			savePath = f"{Folder}/{Name}"
			InfoLi = [tokenStr, ID, savePath]
			Li.append(InfoLi)
		pool = multiprocessing.Pool(2)  # 可以设置线程数，不宜过大
		pool.map(SentinelDownload.Download1, Li)


if __name__ == '__main__':

	# todo 设置参数
	Folder = r"./SentinelTest"  # todo 保存路径
	userName = "xxxxxxx"  # todo 用户名
	password = "xxxxxxx"  # todo 密码

	with open("SearchURL.txt", mode="r") as f:
		urlString = f.read()  # 网页获取的url,顾及到url过长，故存放在txt文件中

	if not os.path.exists(Folder):
		os.makedirs(Folder)

	# 检索数据
	url = SentinelDownload.CreatURL(urlString)
	dataInfo = SentinelDownload.Search(url)
	print("检索完成，共检索到%d条数据信息" % len(dataInfo))

	# 获取token
	tokenStr = SentinelDownload.GetAccessToken(username=userName, password=password)

	# 下载数据
	# SentinelDownload.DownloadMain(DownloadInfoS=dataInfo, token=tokenStr, saveFolder=Folder)  # 单一进程下载
	SentinelDownload.MultiDownload(DownloadInfoS=dataInfo, tokenStr=tokenStr, Folder=Folder)  # 多进程下载
