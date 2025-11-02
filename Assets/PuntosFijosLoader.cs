using System.Collections.Generic;
using System.IO;
using UnityEngine;

[System.Serializable]
public class PuntoFijo
{
    public int x;
    public int y;
}

[System.Serializable]
public class PuntosData
{
    public List<PuntoFijo> puntos_entrega;
    public List<PuntoFijo> puntos_recarga;
}

public class PuntosFijosLoader : MonoBehaviour
{
    public string jsonFileName = "puntos_fijos.json";
    public GameObject prefabEntrega;  // Prefab rojo
    public GameObject prefabRecarga;  // Prefab amarillo

    private PuntosData puntosData;

    void Start()
    {
        string path;

        #if UNITY_EDITOR
        path = Path.Combine(Application.streamingAssetsPath, jsonFileName);
        #else

        string exeDir = System.IO.Path.GetDirectoryName(Application.dataPath);
        path = Path.Combine(exeDir, "Puntos");
        path = Path.Combine(path, jsonFileName);
        #endif

        if (File.Exists(path))
        {
            string jsonText = File.ReadAllText(path);
            puntosData = JsonUtility.FromJson<PuntosData>(jsonText);

            if (puntosData != null)
            {
                MostrarPuntos();
            }
            else
            {
                Debug.LogWarning("No se pudo leer el archivo de puntos fijos.");
            }
        }
        else
        {
            Debug.LogError("Archivo JSON no encontrado en: " + path);
        }
    }

    void MostrarPuntos()
    {
        if (puntosData.puntos_entrega != null)
        {
            foreach (var p in puntosData.puntos_entrega)
            {
                Vector3 pos = new Vector3(p.x, 0, p.y);
                Instantiate(prefabEntrega, pos, Quaternion.identity);
            }
        }

        if (puntosData.puntos_recarga != null)
        {
            foreach (var p in puntosData.puntos_recarga)
            {
                Vector3 pos = new Vector3(p.x, 0, p.y);
                Instantiate(prefabRecarga, pos, Quaternion.identity);
            }
        }
    }
}
