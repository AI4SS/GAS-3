<p align="center">
  <img src="https://img.shields.io/badge/ACL%202025-Findings-blueviolet?style=flat-square">
</p>

<h1 align="center"><strong>GA-S<sup>3</sup>: Comprehensive Social Network Simulation with Group Agents</strong></h1>

<p align="center">
  <em>Accepted by ACL 2025 Findings</em>
</p>

<p align="center">
  🎉 <strong>We have open-sourced the runnable codebase of GA-S<sup>3</sup>.</strong>
</p>

---

GA-S<sup>3</sup> is a comprehensive social network simulation system built around newly designed Group Agents.
Unlike conventional agent systems that simulate one individual at a time, our Group Agents represent collections of individuals with similar online behaviors, making large-scale and realistic social simulation possible at manageable computational cost.

In this release, we open-source:

- 📦 Codebase
- 🧠 Group agent generation modules
- 🌐 Social environment configuration
- 🔧 benchmark-compatible simulation pipeline


<p align="center">
  <img src="./assets/overview.png" alt="Overview of our social network simulation system." width="88%">
</p>

---

## 🚀 Set-up

Install the dependencies:

```bash
pip install -r requirements.txt
```

Then check the examples in:

- [`config/settings.example.yaml`](./config/settings.example.yaml)

Copy `config/settings.example.yaml` to `config/settings.yaml`, then fill in your own model configuration and runtime settings there.
In particular, please provide your own dataset file path in `dataset_path`.

---

## ▶️ Run

After configuration is ready, simply run:

```bash
python main.py
```

---

## 📈 Analysis

After execution, all outputs will be written to the event-specific directory under [`results/`](./results), for example:

- `results/event_7/`

---

### 📚 Citation

If you use GA-S³ in your work, please cite us:

```bibtex
@article{zhang2025ga,
  title={GA-S3: Comprehensive Social Network Simulation with Group Agents},
  author={Zhang, Yunyao and Song, Zikai and Zhou, Hang and Ren, Wenfeng and Chen, Yi-Ping Phoebe and Yu, Junqing and Yang, Wei},
  journal={arXiv preprint arXiv:2506.03532},
  year={2025}
}
```

**GB/T 7714:**  
Zhang Y, Song Z, Zhou H, et al. *GA-S3: Comprehensive Social Network Simulation with Group Agents*[J]. *arXiv preprint arXiv:2506.03532*, 2025.

**MLA:**  
Zhang, Yunyao, et al. "*GA-S3: Comprehensive Social Network Simulation with Group Agents.*" *arXiv preprint arXiv:2506.03532* (2025).

**APA:**  
Zhang, Y., Song, Z., Zhou, H., Ren, W., Chen, Y. P. P., Yu, J., & Yang, W. (2025). *GA-S3: Comprehensive Social Network Simulation with Group Agents*. *arXiv preprint arXiv:2506.03532*.
