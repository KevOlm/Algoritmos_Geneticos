using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

//Datos del JSON
[System.Serializable]
public class Punto
{
    public int x;
    public int y;
}

[System.Serializable]
public class Individuo
{
    public List<Punto> individuo;
    public float fitness;
}

[System.Serializable]
public class Generacion
{
    public int generacion;
    public List<Individuo> rutas;
}

public class RutasdesdeJSON : MonoBehaviour
{
    public string jsonFileName = "rutas_generaciones.json";
    public GameObject cubePrefab;
    public float moveSpeed = 4f;
    public float delayEntreGeneraciones = 15f;
    public float paso = 2f;
    public TextMesh texto;

    private List<Generacion> generaciones = new List<Generacion>();

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
            generaciones = JsonHelper.FromJson<Generacion>(jsonText);

            if (generaciones != null && generaciones.Count > 0)
            {
                Debug.Log("Generaciones cargadas: " + generaciones.Count);
                StartCoroutine(SimularGeneraciones());
            }
            else
            {
                Debug.LogWarning("No se encontraron generaciones en el archivo JSON.");
            }
        }
        else
        {
            Debug.LogError("Archivo JSON no encontrado en: " + path);
        }
    }

    IEnumerator SimularGeneraciones()
    {
        foreach (Generacion gen in generaciones)
        {
            texto.text = "Generación " + gen.generacion;
            List<GameObject> cubos = new List<GameObject>();

            for (int i = 0; i < gen.rutas.Count; i++)
            {
                List<Punto> ruta = gen.rutas[i].individuo;

                if (ruta == null || ruta.Count == 0)
                {
                    Debug.LogWarning("Ruta vacía o mal formada en generación " + gen.generacion);
                    continue;
                }
                Vector3 inicio = new Vector3(0, 0, 0);
                GameObject cubo = Instantiate(cubePrefab, inicio, Quaternion.identity);
                cubo.name = "G" + gen.generacion + "_I" + i;
                cubos.Add(cubo);

                Renderer renderer = cubo.GetComponent<Renderer>();
                if (renderer != null)
                {
                    float intensidad = Mathf.InverseLerp(300, 100, gen.rutas[i].fitness);
                    renderer.material.color = Color.Lerp(Color.red, Color.green, intensidad);
                }

                string rutaTexto = "(0,0) ";
                foreach (Punto p in ruta)
                {
                    rutaTexto += "(" + p.x + "," + p.y + ") ";
                }
                Debug.Log("Gen " + gen.generacion + ", Ind " + i);

                List<Punto> rutaCompleta = new List<Punto>();
                rutaCompleta.Add(new Punto { x = 0, y = 0 });
                rutaCompleta.AddRange(ruta);
                rutaCompleta.Add(new Punto { x = 0, y = 0 });

                StartCoroutine(MoverCuboPorRuta(cubo, rutaCompleta));
            }

            yield return new WaitForSeconds(delayEntreGeneraciones);

            foreach (GameObject c in cubos)
            {
                if (c != null) Destroy(c);
            }
        }
    }

    IEnumerator MoverCuboPorRuta(GameObject cubo, List<Punto> ruta)
    {
        for (int i = 1; i < ruta.Count; i++)
        {
            Vector3 start = ConvertirCoord(ruta[i - 1]);
            Vector3 end = ConvertirCoord(ruta[i]);

            List<Vector3> pasos = GenerarCaminoCuadricula(start, end);

            foreach (Vector3 destino in pasos)
            {
                if (cubo == null) yield break;

                float t = 0f;
                Vector3 origen = cubo.transform.position;

                while (t < 1f)
                {
                    if (cubo == null) yield break;
                    cubo.transform.position = Vector3.Lerp(origen, destino, t);
                    t += Time.deltaTime * moveSpeed;
                    yield return null;
                }

                cubo.transform.position = destino;
                yield return new WaitForSeconds(0.05f);
            }
        }
    }

    List<Vector3> GenerarCaminoCuadricula(Vector3 inicio, Vector3 fin)
    {
        List<Vector3> camino = new List<Vector3>();
        Vector3 actual = inicio;

        float dx = fin.x - inicio.x;
        float dy = fin.z - inicio.z;

        int pasosX = Mathf.Abs(Mathf.RoundToInt(dx / paso));
        int pasosY = Mathf.Abs(Mathf.RoundToInt(dy / paso));

        int dirX = dx > 0 ? 1 : -1;
        int dirY = dy > 0 ? 1 : -1;

        for (int i = 0; i < pasosX; i++)
        {
            actual = new Vector3(actual.x + paso * dirX, 0, actual.z);
            camino.Add(actual);
        }

        // luego en Y
        for (int j = 0; j < pasosY; j++)
        {
            actual = new Vector3(actual.x, 0, actual.z + paso * dirY);
            camino.Add(actual);
        }

        return camino;
    }

    Vector3 ConvertirCoord(Punto c)
    {
        if (c == null)
            return Vector3.zero;

        return new Vector3(c.x, 0, c.y);
    }
}

public static class JsonHelper
{
    public static List<T> FromJson<T>(string json)
    {
        return JsonUtility.FromJson<Wrapper<T>>("{\"Items\":" + json + "}").Items;
    }

    [System.Serializable]
    private class Wrapper<T>
    {
        public List<T> Items = new List<T>();
    }
}
